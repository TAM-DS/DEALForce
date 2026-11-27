import {createHash} from 'node:crypto';
// Trusted entry point: JSON input only; no client-selected code, paths or tools.
import {readFile} from 'node:fs/promises';
import {ASSETS,VERSION,calculate,validate} from '../web/model.mjs';
let raw='';for await(const chunk of process.stdin){raw+=chunk;if(raw.length>4096)throw Error('Input too large');}
const {asset,assumptions}=JSON.parse(raw);
const fixture=ASSETS.find(x=>x.id===asset);if(!fixture)throw Error('Unknown project');
validate(assumptions);
const evidence=JSON.parse(await readFile(new URL('../web/evidence.json',import.meta.url),'utf8'));
console.log(JSON.stringify({asset:fixture,assumptions,metrics:calculate(fixture,assumptions),modelVersion:VERSION,evidence,evidenceHashes:Object.fromEntries(evidence.map(r=>[r.id,createHash('sha256').update(JSON.stringify(r)).digest('hex')]))}));
