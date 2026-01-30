export function $(id){ return document.getElementById(id); }

export async function postJSON(url, data){
  const res = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(data)
  });
  const payload = await res.json().catch(()=> ({}));
  return { ok: res.ok, status: res.status, payload };
}
