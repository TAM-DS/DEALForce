import {rm,mkdir,cp,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
await rm('dist',{recursive:true,force:true});await mkdir('dist');await cp('web','dist',{recursive:true});
const records=JSON.parse(await readFile('web/evidence.json','utf8'));
const hashes=Object.fromEntries(records.map(r=>[r.id,createHash('sha256').update(JSON.stringify(r)).digest('hex')]));
await writeFile('dist/evidence-manifest.json',JSON.stringify(hashes,null,2));console.log(`Built static workspace with ${records.length} evidence records.`);
