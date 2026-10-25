// Render pages with realistic state, without a browser, camera or HTTP server.
import { mkdir,writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { build } from 'vite';
import React from 'react';
import { renderToString } from 'react-dom/server';

const folder=path.resolve('node_modules/.cache/snooker-render-check');
await mkdir(folder,{recursive:true});
const names=['DashboardPage','ProfilePage','SetupPage','CriteriaPage','TrainingPage','SummaryPage','HistoryPage'];
const entry=path.join(folder,'entry.jsx');
await writeFile(entry,names.map(name=>`export {default as ${name}} from ${JSON.stringify(path.resolve('src/pages',name+'.jsx').replaceAll('\\','/'))};`).join('\n'));
await build({logLevel:'error',build:{ssr:entry,outDir:path.join(folder,'output'),emptyOutDir:false,
  rollupOptions:{output:{entryFileNames:'entry.mjs'}}}});
const pages=await import(pathToFileURL(path.join(folder,'output/entry.mjs')));
const exercise={id:1,module_id:1,module:'Foundation',name:'ท่าทาง',setup:{requires:['side']},
  instructions:'ทดลองท่าทาง',lesson:{goal:'ท่าทาง',camera:'side',steps:['หยุดนิ่ง'],metrics:['elbow_mean']},
  criteria:[{id:1,version:1,approved:false,rules:{}}]};
const fn=()=>{};
const props={user:{username:'check',display_name:'Check',dominant_hand:'RIGHT'},catalog:[exercise],exercise,
  criteria:exercise.criteria[0],units:{elbow_mean:'degree'},loaded:true,busy:false,active:false,
  progress:[],history:[],visibleHistory:[],historyFilter:{exercise:'',from:'',to:'',mode:''},
  pair:['',''],comparison:null,page:'history',exerciseId:'1',criteriaId:'1',
  config:{mode:'LIVE',hand:'RIGHT',side_source:'0',top_source:'1'},advanced:'{}',connected:true,
  prepared:'',fingerprint:'check',frame:{},status:{frame:{},mode:'LIVE',configuration:{}},
  report:{protocol_result:{purpose:'ASSESSMENT',status:'INCOMPLETE',valid_attempts:2,required_valid_attempts:4,invalid_attempts:1,remaining:2,pass_rate:.5,minimum_pass_rate:.75},id:'check',name:'ท่าทาง',started_at:'2026-01-01T00:00:00Z',mode:'LIVE',
    attempts:[{id:'attempt',number:1,status:'INVALID',reason:'ยังไม่ยืนยันเกณฑ์',metrics:{elbow_mean:{value:90,unit:'degree'}},feedback:[],
      quality:{samples:30,duration_s:2,not_ready_frames:0,processing_ms:{mean:20}},
      display_timing:{n:10,median_ms:40,p95_ms:60,clock_uncertainty_ms:1}}],counts:{PASS:0,FAIL:0},pass_rate:null},
  activeReport:{protocol_result:{purpose:'ASSESSMENT',status:'IN_PROGRESS',valid_attempts:2,required_valid_attempts:4,invalid_attempts:1,remaining:2,pass_rate:.5,minimum_pass_rate:.75}},
  lastAttempt:{status:'INVALID',reason:'ยังไม่ยืนยันเกณฑ์',metrics:{},feedback:[]}};
for(const name of ['setPage','load','setCriteriaId','run','choose','setHistoryFilter','setReport','setPair',
  'setComparison','onLogout','setConfig','setAdvanced','checkReady','startSession','setPrepared','setError',
  'navigate','finishAttempt','startAttempt','finishSession','onDisplayed'])props[name]=fn;
let count=0;
for(const [name,Page] of Object.entries(pages)) {
  for(const variant of name==='HistoryPage' ? [{page:'history'},{page:'compare'}] : name==='TrainingPage' ? [{active:false},{active:true,status:{frame:{t:1,images:{side:'AA==',top:'AA=='},image_sizes:{side:[1280,720],top:[1280,720]}},configuration:{table_size:[3500,1750]},mode:'LIVE'}}] : name==='SetupPage' ? [{}, {exercise:{...exercise,module_id:3,setup:{fraction:.5}},advanced:JSON.stringify({table_size:[3500,1750],ball_radius:26})}] : [{}]) {
    const html=renderToString(React.createElement(Page,{...props,...variant}));
    if(!html.length)throw new Error(`${name} rendered empty`);
    count++;
  }
}
console.log(`Page render checks passed: ${count} states`);
