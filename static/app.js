const $ = id => document.getElementById(id);
let spec;
const text = (tag, value, cls) => {const el = document.createElement(tag); el.textContent = value; if(cls) el.className = cls; return el;};
async function api(path, options={}) {
  const response = await fetch(path, {...options, headers:{'Content-Type':'application/json','X-API-Key':$('api-key').value,...options.headers}});
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  return body;
}
function evidence(container, items) {
  container.replaceChildren();
  for(const item of items){const node = text('article','', 'evidence');node.append(text('b',item.id+' · '+item.source),text('p',item.text));container.append(node);}
  if(!items.length) container.append(text('p','No matching policy excerpt. Try a different phrase.','muted'));
}
function loadScenario(){const example=spec.scenarios[Number($('scenario').value)];for(const [key,value] of Object.entries(example.features)) $(key).value=value;}
async function init(){
  try {
    spec=await api('/api/meta');$('error').textContent='';
    $('title').textContent=spec.title;document.title=spec.title;$('problem').textContent=spec.problem;$('domain').textContent=spec.domain.toUpperCase()+' / DECISION INTELLIGENCE';$('repository').href='https://github.com/alavisaqib/'+spec.slug;
    $('mode').textContent=spec.provider==='demo'?'Offline demonstration':'Live LLM provider';document.documentElement.style.setProperty('--accent',spec.accent);
    $('scenario').replaceChildren();spec.scenarios.forEach((s,i)=>{const opt=text('option',s.name);opt.value=i;$('scenario').append(opt);});
    $('fields').replaceChildren();for(const field of spec.fields){const wrapper=document.createElement('div');const label=text('label',field.label);label.htmlFor=field.name;const input=document.createElement('input');Object.assign(input,{id:field.name,type:'number',min:field.min,max:field.max,step:field.integer?'1':'any',required:true});wrapper.append(label,input);$('fields').append(wrapper);}
    $('metrics').replaceChildren();for(const [key,value] of Object.entries(spec.model_metrics)){if(typeof value!=='number')continue;const metric=text('div','','metric');metric.append(text('b',value),text('span',key.replaceAll('_',' ')));$('metrics').append(metric);}
    $('search').value=spec.retrieval_query;loadScenario();
  } catch(error){$('error').textContent=error.message;}
}
$('scenario').addEventListener('change',loadScenario);$('unlock').addEventListener('click',init);
$('decision-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!spec)return;$('submit').disabled=true;$('error').textContent='';
  try {
    const features=Object.fromEntries(spec.fields.map(field=>[field.name,Number($(field.name).value)]));
    const result=await api('/api/decisions',{method:'POST',body:JSON.stringify({features,question:$('question').value,context_budget:Number($('budget').value)})});
    $('welcome').hidden=true;$('result').hidden=false;$('action').textContent=result.advice.action;$('cache').textContent=(result.cache_hit?'Cache hit':'Fresh run')+' · '+result.latency_ms+' ms';
    $('summary').textContent=result.facts.summary;$('rationale').textContent=result.advice.rationale;
    $('signals').replaceChildren();for(const [key,value] of Object.entries(result.facts.signals)){const signal=text('div','','signal');signal.append(text('b',typeof value==='number'?value.toLocaleString(undefined,{maximumFractionDigits:2}):value),text('span',key.replaceAll('_',' ')));$('signals').append(signal);}
    $('budget-note').textContent=result.optimization.reduction_pct+'% smaller prompt estimate. '+result.optimization.measurement+'. This request: '+result.current_request_tokens.input+' input / '+result.current_request_tokens.output+' output provider tokens.';
    $('bars').replaceChildren();for(const [label,units] of [['Full corpus',result.optimization.naive_prompt_units],['Selected',result.optimization.packed_prompt_units]]){const row=text('div','','bar-line'),track=text('div','','bar-track'),bar=text('div','','bar'+(label==='Full corpus'?' naive':''));bar.style.width=Math.min(100,100*units/result.optimization.naive_prompt_units)+'%';track.append(bar);row.append(text('span',label),track,text('span',units+' units'));$('bars').append(row);}
    $('steps').replaceChildren(...result.advice.next_steps.map(step=>text('li',step)));evidence($('evidence'),result.evidence);$('raw').textContent=JSON.stringify(result,null,2);
  }catch(error){$('error').textContent=error.message;}finally{$('submit').disabled=false;}
});
$('search-form').addEventListener('submit',async event=>{event.preventDefault();try{evidence($('search-results'),(await api('/api/search?q='+encodeURIComponent($('search').value))).results);}catch(error){$('search-results').textContent=error.message;}});
init();
