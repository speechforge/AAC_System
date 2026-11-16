"use strict";
window.AACHistory=(()=>{
 const pad=n=>String(n).padStart(2,'0');
 const dateKey=date=>`${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`;
 function groups(messages){const grouped=new Map();for(const item of [...messages].sort((a,b)=>b.created_at-a.created_at)){const key=dateKey(new Date(item.created_at*1000));if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(item)}return [...grouped].map(([date,items])=>({date,items}));}
 function csv(messages){
  const cell=value=>{let text=String(value??'');if(/^[\s]*[=+@-]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"'};
  const rows=[['Date','Time','Language','Message']];
  for(const item of [...messages].sort((a,b)=>b.created_at-a.created_at)){const date=new Date(item.created_at*1000);rows.push([dateKey(date),`${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`,item.language,item.text])}
  return '\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
 }
 return {dateKey,groups,csv};
})();
