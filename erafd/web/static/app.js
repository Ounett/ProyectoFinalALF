'use strict';

const $ = id => document.getElementById(id);
let datos = null;

function texto(id, valor) { $(id).textContent = valor; }

function mostrar(tab) {
  for (const boton of document.querySelectorAll('[data-tab]')) {
    const activo = boton.dataset.tab === tab;
    boton.classList.toggle('activo', activo);
    boton.setAttribute('aria-pressed', String(activo));
  }
  for (const vista of document.querySelectorAll('.vista')) {
    vista.hidden = vista.id !== 'vista-' + tab;
  }
  if (tab === 'diagrama') dibujar();
}

function ponerTabla(id, filas) {
  const tabla = $(id);
  tabla.replaceChildren();
  for (const fila of filas) {
    const tr = document.createElement('tr');
    for (const valor of [fila.from, fila.symbol, fila.to]) {
      const td = document.createElement('td');
      td.textContent = valor;
      tr.appendChild(td);
    }
    tabla.appendChild(tr);
  }
}

function presentar(respuesta) {
  datos = respuesta;
  $('resultados').hidden = false;
  texto('resultado-texto', respuesta.accepted ? 'Cadena aceptada' : 'Cadena rechazada');
  texto('conteo', `AFND: ${respuesta.metrics.nfa_states} estados | AFD: ${respuesta.metrics.dfa_states} estados | Código: ${respuesta.return_code}`);
  texto('recorrido', `${respuesta.trace.join('\n') || '(Sin transiciones: cadena vacía)'}\n${respuesta.accepted ? 'Cadena aceptada' : 'Cadena rechazada'}`);
  texto('afnd-datos', `Inicial: ${respuesta.nfa.start} | Final: ${respuesta.nfa.finals.join(', ')} | Alfabeto: {${respuesta.nfa.symbols.join(', ')}}`);
  texto('afd-datos', `Inicial: ${respuesta.dfa.start} | Finales: {${respuesta.dfa.finals.join(', ')}} | Alfabeto: {${respuesta.dfa.symbols.join(', ')}}`);
  ponerTabla('afnd-tabla', respuesta.nfa.rows);
  ponerTabla('afd-tabla', respuesta.dfa.rows);
  texto('conjuntos', Object.entries(respuesta.dfa.subsets).map(([q, estados]) => `${q} = {${estados.join(', ')}}`).join('\n'));
}

function diagramaBasico(maquina) {
  const ns = 'http://www.w3.org/2000/svg';
  const nodos = maquina.nodes;
  if (!nodos.length || nodos.length > 45) return null;
  const columnas = Math.min(5, Math.max(2, Math.ceil(Math.sqrt(nodos.length))));
  const filas = Math.ceil(nodos.length / columnas);
  const ancho = columnas * 165 + 120;
  const alto = filas * 135 + 100;
  const crear = (tag, atributos={}) => {
    const el = document.createElementNS(ns, tag);
    for (const [k,v] of Object.entries(atributos)) el.setAttribute(k,String(v));
    return el;
  };
  const svg = crear('svg', {xmlns:ns,viewBox:`0 0 ${ancho} ${alto}`,width:ancho,height:alto});
  const defs = crear('defs');
  const marcador = crear('marker',{id:'flecha',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'});
  marcador.appendChild(crear('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#000'}));
  defs.appendChild(marcador);svg.appendChild(defs);
  const posiciones = {};
  nodos.forEach((n,i)=>{posiciones[n.id]={x:100+(i%columnas)*165,y:72+Math.floor(i/columnas)*135};});
  for (const n of nodos) {
    const p = posiciones[n.id];
    if(n.initial) svg.appendChild(crear('line',{x1:p.x-65,y1:p.y,x2:p.x-34,y2:p.y,stroke:'#000','marker-end':'url(#flecha)'}));
  }
  const grupos = new Map();
  for (const arista of maquina.edges) {
    const clave = arista.from + '\0' + arista.to;
    if(!grupos.has(clave)) grupos.set(clave,[]);
    grupos.get(clave).push(arista.label || arista.symbol);
  }
  for (const [clave,etiquetas] of grupos) {
    const [origen,destino] = clave.split('\0');
    const a=posiciones[origen], b=posiciones[destino];
    if (!a || !b) continue;
    const etiqueta=[...new Set(etiquetas)].join(', ').slice(0,38);
    let x,y;
    if(origen===destino) {
      svg.appendChild(crear('path',{d:`M${a.x-18} ${a.y-21} C${a.x-68} ${a.y-104} ${a.x+68} ${a.y-104} ${a.x+18} ${a.y-21}`,fill:'none',stroke:'#000','marker-end':'url(#flecha)'}));
      x=a.x; y=a.y-66;
    } else {
      const dx=b.x-a.x,dy=b.y-a.y,dist=Math.hypot(dx,dy),ux=dx/dist,uy=dy/dist;
      svg.appendChild(crear('line',{x1:a.x+ux*32,y1:a.y+uy*32,x2:b.x-ux*33,y2:b.y-uy*33,stroke:'#000','marker-end':'url(#flecha)'}));
      x=(a.x+b.x)/2+uy*10; y=(a.y+b.y)/2-ux*10;
    }
    const t=crear('text',{x,y,'text-anchor':'middle',fill:'#000','font-size':11});
    t.textContent=etiqueta;svg.appendChild(t);
  }
  for(const n of nodos) {
    const p=posiciones[n.id];
    svg.appendChild(crear('circle',{cx:p.x,cy:p.y,r:30,fill:'#fff',stroke:'#000','stroke-width':1.5}));
    if(n.final) svg.appendChild(crear('circle',{cx:p.x,cy:p.y,r:25,fill:'none',stroke:'#000'}));
    const t=crear('text',{x:p.x,y:p.y+4,'text-anchor':'middle',fill:'#000','font-size':13});
    t.textContent=n.id;svg.appendChild(t);
  }
  return svg;
}

function dibujar() {
  const contenedor=$('dibujo');contenedor.replaceChildren();
  if(!datos) return;
  if(datos.graph_limited) {
    texto('nota-diagrama','El autómata es muy grande. Consulta las tablas.');
    return;
  }
  const tipo=$('tipo-diagrama').value;
  const svg=datos.graph_svg[tipo];
  if(svg) {
    const blob = new Blob([svg],{type:'image/svg+xml;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const img=document.createElement('img');
    img.alt=`Diagrama ${tipo==='dfa'?'AFD':'AFND'}`;
    img.src=url;
    img.addEventListener('load',()=>URL.revokeObjectURL(url),{once:true});
    contenedor.appendChild(img);
    texto('nota-diagrama','');
  } else {
    const dibujo=diagramaBasico(datos.diagrams[tipo]);
    if(dibujo) {
      contenedor.appendChild(dibujo);
      texto('nota-diagrama','Diagrama básico. Opcional: instala Graphviz para diagramas más claros.');
    } else texto('nota-diagrama','Diagrama demasiado grande para la vista básica. Instala Graphviz o consulta las tablas.');
  }
}

async function convertir(evento) {
  evento.preventDefault();
  const boton=$('convertir');boton.disabled=true;boton.textContent='Procesando...';
  $('error').hidden=true;
  try {
    const respuesta=await fetch('/api/convert',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expression:$('expresion').value,chain:$('cadena').value})
    });
    let json;
    try {
      json = await respuesta.json();
    } catch {
      throw Error('El servidor devolvió una respuesta inválida.');
    }
    if(!respuesta.ok) throw Error(json.error || 'No se pudo analizar la expresión.');
    presentar(json);
    mostrar('recorrido');
  } catch(e) {
    $('error').textContent='Error: '+e.message;
    $('error').hidden=false;
    $('resultados').hidden=true;
    datos=null;
  } finally {
    boton.disabled=false;boton.textContent='Convertir y evaluar';
  }
}

$('formulario').addEventListener('submit',convertir);
$('limpiar').addEventListener('click',()=>{
  $('expresion').value='';$('cadena').value='';
  $('resultados').hidden=true;$('error').hidden=true;datos=null;
  $('expresion').focus();
});
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>mostrar(b.dataset.tab)));
$('tipo-diagrama').addEventListener('change',dibujar);
document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){
    e.preventDefault();$('formulario').requestSubmit();
  }
});
