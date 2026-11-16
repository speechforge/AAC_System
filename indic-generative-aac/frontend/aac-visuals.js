/* Local, code-native symbol drawings and low-glare button palettes. */
(function () {
  const e = React.createElement;
  const THEMES = [
    ['sky','Sky','#e3ebf4','#d3e0ee','#2d4257'],
    ['sage','Sage','#e3ece3','#d1e0d1','#30493d'],
    ['teal','Teal','#deecea','#cae0dc','#284748'],
    ['lavender','Lavender','#eae6f3','#dcd5eb','#433d58'],
    ['rose','Rose','#f2e3e7','#e9cfd7','#523b45'],
    ['peach','Peach','#f4e7db','#ead8c6','#554335'],
    ['sand','Sand','#eeeadd','#e1dac7','#504b33'],
    ['olive','Olive','#e8ebdc','#d8dec7','#414b32'],
    ['slate','Slate','#e4e9ed','#d3dce3','#3d4650'],
    ['cocoa','Cocoa','#ece4df','#dfd2ca','#50413b'],
    ['mauve','Mauve','#eee3ed','#e0d0df','#4d3e4e'],
    ['blue','Blue','#e2e7f3','#d0d9ed','#35425d']
  ].map(([id,name,light,hover,dark])=>({id,name,light,hover,dark,lightText:'#172331',darkText:'#f7fafc'}));
  const STYLES=[{id:'emoji',label:'Emoji symbols'},{id:'line',label:'Line drawings'},{id:'contrast',label:'High-contrast icons'},{id:'photo',label:'Real photos'},{id:'text',label:'Text only'}];
  const PLAYBACK_SPEEDS=[0.25,0.5,0.75,1,1.25,1.5,1.75,2,3];
  function themeVariables(id,dark,highContrast){
    const t=THEMES.find(t=>t.id===id)||THEMES[0];
    const bg=highContrast?(dark?'#000000':'#ffffff'):(dark?t.dark:t.light);
    const fg=highContrast?(dark?'#ffffff':'#000000'):(dark?t.darkText:t.lightText);
    return {'--button-bg':bg,'--button-fg':fg,'--button-hover':highContrast?bg:(dark?t.dark:t.hover),'--button-border':dark?'#82929f':'#677889','--button-selected-bg':fg,'--button-selected-fg':bg};
  }
  const path=(d)=>'<path d="'+d+'"/>';
  const face=(mouth,eyes='<path d="M8 9h.01M16 9h.01"/>')=>'<circle cx="12" cy="12" r="9"/>'+eyes+path(mouth);
  const person='<circle cx="12" cy="6" r="3"/><path d="M5 21v-4a7 7 0 0 1 14 0v4M8 21v-5M16 21v-5"/>';
  const glass='<path d="M5 3h14l-2 18H7L5 3ZM6 9h12"/>';
  const cup='<path d="M4 8h12v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V8ZM16 9h2a3 3 0 0 1 0 6h-2M7 3v2M12 3v2"/>';
  const book='<path d="M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2V4ZM12 6v15"/>';
  const heart='<path d="M20 5a5 5 0 0 0-8 1 5 5 0 0 0-8-1C-2 11 12 21 12 21S26 11 20 5Z"/>';
  const hand='<path d="M7 13V5a1.5 1.5 0 0 1 3 0v6-8a1.5 1.5 0 0 1 3 0v8-7a1.5 1.5 0 0 1 3 0v7-4a1.5 1.5 0 0 1 3 0v9c0 7-10 8-13 3l-3-5c-1-2 1-3 2-2l2 2Z"/>';
  const shapes={
    YES:path('M4 12l5 5L20 6'),NO:path('M5 5l14 14M19 5 5 19'),MORE:path('M12 4v16M4 12h16'),
    STOP:'<path d="m8 2 8 0 6 6v8l-6 6H8l-6-6V8l6-6Z"/><path d="M8 8v8M12 8v8M16 8v8"/>',
    WANT:hand,HELP:hand+path('M20 2v5M17.5 4.5h5'),
    ME:person+path('M1 12h7M5 9l3 3-3 3'),YOU:person+path('M16 12h7M20 9l3 3-3 3'),
    GOOD:path('M7 10v11H3V10h4ZM7 10l5-8c3 0 2 5 1 7h6c2 0 2 2 1 4l-2 7H7'),
    BAD:path('M7 14V3H3v11h4ZM7 14l5 8c3 0 2-5 1-7h6c2 0 2-2 1-4l-2-7H7'),
    EAT:path('M3 3v6a3 3 0 0 0 6 0V3M6 3v19M17 3v19M17 3c6 4 6 10 0 10'),
    DRINK:glass+path('m14 8 2-6h5'),WATER:glass+path('M9 14c0 3 6 3 6 0'),MILK:glass,
    FOOD:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="5"/><path d="M1 3v18M23 3v18"/>',
    RICE:'<path d="M3 12h18c0 12-18 12-18 0ZM7 8l2 1M12 6l1 2M16 8l2-1M7 5l1-1"/>',
    ROTI:'<circle cx="12" cy="12" r="9"/><path d="M8 8h.01M15 6h.01M17 13h.01M7 15h.01M12 12h.01M13 18h.01"/>',
    FRUIT:'<path d="M12 7c-6-6-13 2-7 11 3 5 5 1 7 2 3 2 7 1 9-6 3-8-5-11-9-7ZM12 7c0-4 3-5 6-5-1 4-3 5-6 5Z"/>',
    TEA:cup,JUICE:glass+path('m14 8 2-6h5'),SNACK:'<circle cx="12" cy="12" r="9"/><path d="M8 8h.01M15 7h.01M17 13h.01M7 15h.01M12 12h.01M13 18h.01"/>',
    PIZZA:'<path d="M3 4c6-3 12-3 18 0L12 22 3 4ZM4 7c5-2 11-2 16 0"/><circle cx="10" cy="11" r="1"/><circle cx="14" cy="8" r="1"/>',
    PLAY:'<path d="M7 8h10c6 0 7 12 3 12l-4-4H8l-4 4C0 20 1 8 7 8ZM6 10v6M3 13h6M16 11h.01M19 14h.01"/>',
    SLEEP:'<path d="M3 8v13M3 17h18v4M3 14h18v3M8 10h13v4"/><circle cx="6" cy="11" r="2"/><path d="M13 2h6l-6 5h6"/>',
    GO:path('M3 12h18M14 5l7 7-7 7'),STUDY:book,WRITE:book+path('m16 2 3 3M10 11l9-9 3 3-9 9-4 1 1-4Z'),
    BATH:'<path d="M2 12h20c0 11-20 11-20 0ZM5 12V5a3 3 0 0 1 6 0M8 6h6M6 21v1M18 21v1"/>',
    CALL:path('M5 2 2 5c0 8 9 17 17 17l3-3-5-5-3 2c-3-1-5-3-6-6l2-3-5-5Z'),
    LOOK:'<path d="M2 12c5-10 15-10 20 0-5 10-15 10-20 0Z"/><circle cx="12" cy="12" r="3"/>',
    HAPPY:face('M7 14c2 5 8 5 10 0'),SAD:face('M7 17c2-5 8-5 10 0'),ANGRY:face('M7 17c2-3 8-3 10 0','<path d="m6 7 4 2m8-2-4 2"/>'),
    TIRED:face('M8 16h8','<path d="M6 10h4M14 10h4"/>'),SICK:face('M8 16h5M16 13v7','<path d="M6 9h4M14 9h4"/>'),SCARED:face('M10 16a2 3 0 1 0 4 0 2 3 0 1 0-4 0'),
    LOVE:heart,EXCITED:face('M7 13h10c-1 7-9 7-10 0'),
    MOTHER:person+path('M7 6c-2 1-3 5-2 8M17 6c2 1 3 5 2 8'),FATHER:person,SISTER:person,BROTHER:person,
    TEACHER:person+path('M1 2h7M18 2h5v10h-3'),DOCTOR:person+path('M10 15h4M12 13v4'),FRIEND:'<circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><path d="M1 21v-4a6 6 0 0 1 12 0v4M11 21v-4a6 6 0 0 1 12 0v4"/>',
    HOME:'<path d="m2 11 10-9 10 9M5 9v13h14V9M10 22v-8h4v8"/>',
    SCHOOL:'<path d="m2 9 10-7 10 7M4 8v14h16V8M10 22v-7h4v7M7 11h1M16 11h1M12 2v5h6"/>',
    HOSPITAL:'<path d="M3 22V6h18v16M9 6V2h6v4M10 10h4M12 8v4M10 22v-6h4v6M6 15h1M17 15h1"/>',
    TOILET:'<path d="M5 3h10v9H5V3ZM3 12h18c0 5-4 7-7 7v3H9v-5M7 6h3"/>',ROOM:'<path d="M3 7v15M3 17h18v5M3 11h18v6M5 11V7h6v4"/>',
    MARKET:'<path d="M2 8 5 2h14l3 6M2 8c0 5 5 5 5 0 0 5 5 5 5 0 0 5 5 5 5 0 0 5 5 5 5 0M4 12v10h16V12M9 22v-8h6v8"/>',
    LUNGS:'<path d="M12 2v9M12 7c-3-8-11 8-9 13 1 2 7 1 9-3 2 4 8 5 9 3 2-5-6-21-9-13ZM12 11l-5 4M12 11l5 4"/>',
    HEART:heart+'<path d="M3 12h4l2-4 3 8 2-4h7"/>',BRAIN:'<path d="M12 3c-4-3-7 0-7 3-6 1-5 9-2 10-1 6 6 9 9 3 3 6 10 3 9-3 3-1 4-9-2-10 0-3-3-6-7-3ZM12 3v16M6 7l2 2M4 13l3-1M16 8l3 1M15 16l4-2"/>',
    BONE:'<path d="M8 7c0-7-8-6-6 0-5 3 1 9 5 5l5 5c-4 4 2 10 5 5 6 2 7-6 0-6L8 7Z"/>',
    TOOTH:'<path d="M12 4C-1-5 0 12 6 21c3 5 3-9 6-9s3 14 6 9C24 12 25-5 12 4Z"/>',EYE:'<path d="M2 12c5-10 15-10 20 0-5 10-15 10-20 0Z"/><circle cx="12" cy="12" r="3"/>',
    EAR:'<path d="M7 8c0-10 15-8 13 2-1 4-6 5-6 9-1 5-8 4-8-1M10 9c0-4 6-4 6 0 0 3-4 3-4 6"/>',NOSE:'<path d="M10 2c1 8-6 13-3 15 2 2 3 0 5 2 2-2 3 0 5-2 2-2 0-5-1-7M8 17h.01M16 17h.01"/>',
    NAMASTE:hand,THANKS:heart,HOW:'<circle cx="12" cy="12" r="10"/><path d="M8 8c0-5 9-5 9 0 0 3-5 3-5 6M12 18h.01"/>',BYE:hand,PLEASE:hand,
    HELP_EMERGENCY:'<path d="M12 2 23 22H1L12 2ZM12 8v7M12 18h.01"/>',PAIN:'<path d="m13 2-9 12h7l-1 8 10-13h-8l1-7Z"/>',
    MEDICINE:'<path d="m4 12 8-8c8-8 16 0 8 8l-8 8c-8 8-16 0-8-8ZM8 8l8 8"/>',AMBULANCE:'<path d="M2 6h13v13H2V6ZM15 10h4l3 5v4h-7M6 11h5M8.5 8.5v5M16 15h6"/><circle cx="6" cy="20" r="2"/><circle cx="18" cy="20" r="2"/>',
    FIRE:'<path d="M12 2c0 6-8 7-8 13 0 12 22 9 15-3-2-4-2-5-2-6 0 5-3 5-3 5 1-4-2-9-2-9Z"/>'
  };
  function Drawing({id,contrast}){
    return e('span',{className:'symbol-drawing'+(contrast?' symbol-contrast':''),'aria-hidden':true},e('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor',strokeWidth:contrast?2.8:1.7,strokeLinecap:'round',strokeLinejoin:'round',dangerouslySetInnerHTML:{__html:shapes[id]||'<rect x="3" y="3" width="18" height="15" rx="4"/><path d="m7 18-2 4 7-4M8 9h8M8 13h5"/>'}}));
  }
  function SymbolVisual({item,style,photos}){
    const id=item.k||item.cid||'';
    const photo=(photos||{})[id]||item.image||(window.AAC_PHOTOS||{})[id]?.src;
    const [failed,setFailed]=React.useState(false);
    React.useEffect(()=>setFailed(false),[photo]);
    if(style==='text')return null;
    if(style==='photo'&&photo&&!failed)return e('img',{className:'symbol-photo',src:photo,alt:'',draggable:false,loading:'lazy',onError:()=>setFailed(true)});
    if(style==='line'||style==='contrast'||style==='photo')return e(Drawing,{id,contrast:style==='contrast'});
    return e('span',{className:'symbol-emoji','aria-hidden':true},item.e||item.emoji||'💬');
  }
  const formatSpeed=rate=>Number.isInteger(rate)?rate+'×':rate.toFixed(2)+'×';
  window.AAC_VISUALS={THEMES,STYLES,PLAYBACK_SPEEDS,formatSpeed,themeVariables,SymbolVisual};
})();
