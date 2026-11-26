export function canonical(x){if(x===null||typeof x!=='object')return JSON.stringify(x);if(Array.isArray(x))return '['+x.map(canonical).join(',')+']';return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';}
export async function sha(text){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(b=>b.toString(16).padStart(2,'0')).join('');}
export async function append(log,type,data){const body={seq:log.length+1,time:new Date().toISOString(),type,data,prev:log.at(-1)?.hash??'genesis'};return [...log,{...body,hash:await sha(canonical(body))}];}
export async function verify(log){if(!Array.isArray(log))return false;let prev='genesis';for(let i=0;i<log.length;i++){const {hash,...body}=log[i];if(body.seq!==i+1||body.prev!==prev||hash!==await sha(canonical(body)))return false;prev=hash;}return true;}
export const snapshot=(asset,assumptions,evidence,modelVersion)=>({asset,assumptions,evidence,modelVersion});
export async function validReview(review,current){return !!review&&review.snapshot===await sha(canonical(current));}
