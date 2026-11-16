/* Phase 1 communication surface. Existing account, My Words, Voice and Support drawers stay in index.html. */
window.AACPhaseOne = function AACPhaseOne({
  language,
  tokens,
  setTokens,
  inputText,
  setInputText,
  profile,
  rate,
  autoPronounce,
  onSoundChange,
  onWord,
  renderSymbol,
  support,
  keyboard
}) {
  const {
      useState,
      useEffect,
      useRef
    } = React,
    L = window.AACVNext,
    B = L.board;
  const labels = {
    en: {
      home: 'Home',
      core: 'Core words',
      actions: 'Actions',
      food: 'Food & drink',
      feelings: 'Feelings',
      people: 'People',
      places: 'Places',
      body: 'Health & body',
      chat: 'Social',
      emergency: 'Urgent',
      help: 'Help',
      water: 'Water',
      bathroom: 'Bathroom',
      pain: 'Pain',
      draft: 'Your message',
      typed: 'Type your exact words',
      words: 'Use selected words',
      useTyped: 'Use typed text',
      ready: 'Text ready to speak',
      speak: 'Speak',
      stop: 'Stop audio',
      undo: 'Undo',
      polish: 'Polish',
      use: 'Use suggestion',
      show: 'Show message',
      close: 'Close',
      suggestion: 'Suggestion — review before using',
      refusal: 'Refusal',
      act: 'Intent',
      polarity: 'Polarity',
      auto: 'Auto',
      positive: 'Positive',
      negative: 'Negative',
      REQUEST: 'Request',
      FEELING: 'Feeling',
      FEELING_REQUEST: 'Feeling and request',
      QUESTION: 'Question',
      GREETING: 'Social expression',
      UNKNOWN: 'Not clear yet',
      clarify: 'Please clarify the message. You can keep editing or speak your own words.',
      repeat: 'Repeated No: choose the intended polarity or edit the words.',
      angry: 'Angry + Food: is this anger about food, or a feeling and a request for food?',
      about: 'Keep “angry about food” as my wording',
      both: 'Feeling and request',
      conflict: 'The chosen polarity differs from the selected words. Your explicit choice will be sent.',
      literal: 'No checked suggestion. Your exact words remain available.',
      search: 'Find a word',
      results: 'Temporary results',
      setup: 'Set up offline phrases',
      offline: 'Offline audio',
      localVoice: 'Use matching on-device voice',
      history: 'Capture spoken-message history',
      vibration: 'Vibration',
      sound: 'Pronounce selected words',
      last: 'Last spoken / shown',
      install: 'Offline phrases installed',
      notReady: 'Offline pack not installed yet. Set it up while online.',
      freeze: 'Results are held while you use this region.',
      more: 'More',
      previous: 'Previous',
      next: 'Next',
      clear: 'Clear draft',
      language: 'Message language',
      suggestions: 'Predictions',
      noAudio: 'Audio unavailable. You can show the exact message.',
      own: 'Speak my exact selected words',
      layout: 'Saved layout',
      legacy: 'Existing board',
      large: 'Large touch',
      text: 'Text first',
      preview: 'Preview layout',
      save: 'Save layout',
      cancel: 'Cancel',
      original: 'Draft kept below',
      requestError: 'Suggestion unavailable. Keep editing, show or speak your own words.',
      public: 'Public board — sign in for personal data',
      changeLanguage: 'This message keeps its original speech language. Edit its language or regenerate to change it.'
    },
    hi: {
      home: 'होम',
      core: 'मुख्य शब्द',
      actions: 'क्रियाएँ',
      food: 'खाना और पेय',
      feelings: 'भावनाएँ',
      people: 'लोग',
      places: 'जगहें',
      body: 'स्वास्थ्य और शरीर',
      chat: 'सामाजिक',
      emergency: 'ज़रूरी',
      help: 'मदद',
      water: 'पानी',
      bathroom: 'बाथरूम',
      pain: 'दर्द',
      draft: 'आपका संदेश',
      typed: 'अपने शब्द लिखें',
      words: 'चुने शब्द इस्तेमाल करें',
      useTyped: 'लिखा पाठ इस्तेमाल करें',
      ready: 'बोलने के लिए तैयार पाठ',
      speak: 'बोलें',
      stop: 'आवाज़ रोकें',
      undo: 'पहले जैसा करें',
      polish: 'सुधार सुझाएँ',
      use: 'सुझाव इस्तेमाल करें',
      show: 'संदेश दिखाएँ',
      close: 'बंद करें',
      suggestion: 'सुझाव — पहले जाँचें',
      refusal: 'इनकार',
      act: 'आशय',
      polarity: 'सकारात्मक / नकारात्मक',
      auto: 'स्वतः',
      positive: 'सकारात्मक',
      negative: 'नकारात्मक',
      REQUEST: 'अनुरोध',
      FEELING: 'भावना',
      FEELING_REQUEST: 'भावना और अनुरोध',
      QUESTION: 'प्रश्न',
      GREETING: 'अभिवादन',
      UNKNOWN: 'अभी स्पष्ट नहीं',
      clarify: 'संदेश स्पष्ट करें। आप लिखना जारी रख सकते हैं या अपने शब्द बोल सकते हैं।',
      repeat: 'कई बार नहीं: आशय चुनें या शब्द बदलें।',
      angry: 'गुस्सा + खाना: खाने पर गुस्सा है, या भावना के साथ खाने का अनुरोध?',
      about: '“खाने पर गुस्सा” मेरे शब्द रखें',
      both: 'भावना और अनुरोध',
      conflict: 'चुना आशय शब्दों से अलग है। आपका चुनाव इस्तेमाल होगा।',
      literal: 'जाँचा हुआ सुझाव नहीं मिला। अपने शब्द उपलब्ध हैं।',
      search: 'शब्द खोजें',
      results: 'अस्थायी नतीजे',
      setup: 'ऑफ़लाइन वाक्य तैयार करें',
      offline: 'ऑफ़लाइन आवाज़',
      localVoice: 'डिवाइस की इसी भाषा की आवाज़',
      history: 'बोले संदेशों का इतिहास रखें',
      vibration: 'कंपन',
      sound: 'चुने शब्द बोलें',
      last: 'अंतिम बोला / दिखाया संदेश',
      install: 'ऑफ़लाइन वाक्य तैयार हैं',
      notReady: 'ऑफ़लाइन पैक तैयार नहीं है। इंटरनेट रहते सेटअप करें।',
      freeze: 'इस्तेमाल करते समय नतीजे स्थिर रहते हैं।',
      more: 'और',
      previous: 'पिछला',
      next: 'अगला',
      clear: 'संदेश मिटाएँ',
      language: 'संदेश की भाषा',
      suggestions: 'अगले शब्द',
      own: 'मेरे चुने शब्द बोलें',
      layout: 'सहेजा लेआउट',
      legacy: 'मौजूदा बोर्ड',
      large: 'बड़े बटन',
      text: 'पहले पाठ',
      preview: 'लेआउट देखें',
      save: 'लेआउट सहेजें',
      cancel: 'रद्द करें',
      changeLanguage: 'यह संदेश अपनी मूल भाषा में रहेगा। बदलने के लिए उसकी भाषा बदलें या नया सुझाव लें।'
    },
    gu: {
      home: 'હોમ',
      core: 'મુખ્ય શબ્દો',
      actions: 'ક્રિયાઓ',
      food: 'ખોરાક અને પીણાં',
      feelings: 'લાગણીઓ',
      people: 'લોકો',
      places: 'જગ્યાઓ',
      body: 'સ્વાસ્થ્ય અને શરીર',
      chat: 'સામાજિક',
      emergency: 'તાત્કાલિક',
      help: 'મદદ',
      water: 'પાણી',
      bathroom: 'બાથરૂમ',
      pain: 'દુખાવો',
      draft: 'તમારો સંદેશ',
      typed: 'તમારા શબ્દો લખો',
      words: 'પસંદ કરેલા શબ્દો વાપરો',
      useTyped: 'લખેલું વાપરો',
      ready: 'બોલવા માટે તૈયાર લખાણ',
      speak: 'બોલો',
      stop: 'અવાજ રોકો',
      undo: 'પાછું કરો',
      polish: 'સુધારો સૂચવો',
      use: 'સૂચન વાપરો',
      show: 'સંદેશ બતાવો',
      close: 'બંધ કરો',
      suggestion: 'સૂચન — પહેલાં તપાસો',
      refusal: 'ઇનકાર',
      act: 'ઉદ્દેશ',
      polarity: 'હકાર / નકાર',
      auto: 'આપોઆપ',
      positive: 'હકારાત્મક',
      negative: 'નકારાત્મક',
      REQUEST: 'વિનંતી',
      FEELING: 'લાગણી',
      FEELING_REQUEST: 'લાગણી અને વિનંતી',
      QUESTION: 'પ્રશ્ન',
      GREETING: 'અભિવાદન',
      UNKNOWN: 'હજુ સ્પષ્ટ નથી',
      clarify: 'સંદેશ સ્પષ્ટ કરો. તમે લખવાનું ચાલુ રાખી શકો અથવા તમારા શબ્દો બોલી શકો.',
      repeat: 'એકથી વધુ ના: ઉદ્દેશ પસંદ કરો અથવા શબ્દો બદલો.',
      angry: 'ગુસ્સો + ખોરાક: ખોરાક વિશે ગુસ્સો છે કે લાગણી સાથે ખોરાકની વિનંતી?',
      about: '“ખોરાક વિશે ગુસ્સો” મારા શબ્દો રાખો',
      both: 'લાગણી અને વિનંતી',
      conflict: 'પસંદ કરેલો ઉદ્દેશ શબ્દોથી જુદો છે. તમારી પસંદગી વપરાશે.',
      literal: 'ચકાસેલું સૂચન નથી. તમારા શબ્દો ઉપલબ્ધ છે.',
      search: 'શબ્દ શોધો',
      results: 'કામચલાઉ પરિણામો',
      setup: 'ઑફલાઇન વાક્યો તૈયાર કરો',
      offline: 'ઑફલાઇન અવાજ',
      localVoice: 'ઉપકરણનો આ ભાષાનો અવાજ',
      history: 'બોલેલા સંદેશોનો ઇતિહાસ રાખો',
      vibration: 'કંપન',
      sound: 'પસંદ કરેલા શબ્દો બોલો',
      last: 'છેલ્લો બોલેલો / બતાવેલો સંદેશ',
      install: 'ઑફલાઇન વાક્યો તૈયાર છે',
      notReady: 'ઑફલાઇન પેક તૈયાર નથી. ઇન્ટરનેટ હોય ત્યારે સેટઅપ કરો.',
      freeze: 'વાપરતી વખતે પરિણામો સ્થિર રહે છે.',
      previous: 'પાછલું',
      next: 'આગળ',
      clear: 'સંદેશ સાફ કરો',
      language: 'સંદેશની ભાષા',
      suggestions: 'આગળના શબ્દો',
      layout: 'સાચવેલું લેઆઉટ',
      legacy: 'હાલનું બોર્ડ',
      large: 'મોટાં બટન',
      text: 'પહેલાં લખાણ',
      preview: 'લેઆઉટ જુઓ',
      save: 'લેઆઉટ સાચવો',
      cancel: 'રદ કરો',
      changeLanguage: 'આ સંદેશ તેની મૂળ ભાષામાં રહેશે. બદલવા માટે તેની ભાષા બદલો અથવા નવું સૂચન મેળવો.'
    },
    mr: {
      home: 'मुख्य पान',
      core: 'मुख्य शब्द',
      actions: 'कृती',
      food: 'अन्न आणि पेये',
      feelings: 'भावना',
      people: 'लोक',
      places: 'ठिकाणे',
      body: 'आरोग्य आणि शरीर',
      chat: 'सामाजिक',
      emergency: 'तातडीचे',
      help: 'मदत',
      water: 'पाणी',
      bathroom: 'शौचालय',
      pain: 'वेदना',
      draft: 'तुमचा संदेश',
      typed: 'तुमचे शब्द लिहा',
      words: 'निवडलेले शब्द वापरा',
      useTyped: 'लिहिलेला मजकूर वापरा',
      ready: 'बोलण्यासाठी तयार मजकूर',
      speak: 'बोला',
      stop: 'आवाज थांबवा',
      undo: 'मागे जा',
      polish: 'सुधारणा सुचवा',
      use: 'सूचना वापरा',
      show: 'संदेश दाखवा',
      close: 'बंद करा',
      suggestion: 'सूचना — आधी तपासा',
      refusal: 'नकार',
      act: 'हेतू',
      polarity: 'होकार / नकार',
      auto: 'आपोआप',
      positive: 'होकारार्थी',
      negative: 'नकारार्थी',
      REQUEST: 'विनंती',
      FEELING: 'भावना',
      FEELING_REQUEST: 'भावना आणि विनंती',
      QUESTION: 'प्रश्न',
      GREETING: 'अभिवादन',
      UNKNOWN: 'अजून स्पष्ट नाही',
      clarify: 'संदेश स्पष्ट करा. तुम्ही लिहित राहू शकता किंवा स्वतःचे शब्द बोलू शकता.',
      repeat: 'एकाहून अधिक नाही: हेतू निवडा किंवा शब्द बदला.',
      angry: 'राग + अन्न: अन्नाबद्दल राग आहे की भावनेसह अन्नाची विनंती?',
      about: '“अन्नाबद्दल राग” माझे शब्द ठेवा',
      both: 'भावना आणि विनंती',
      conflict: 'निवडलेला हेतू शब्दांपेक्षा वेगळा आहे. तुमची निवड वापरली जाईल.',
      literal: 'तपासलेली सूचना नाही. तुमचे शब्द उपलब्ध आहेत.',
      search: 'शब्द शोधा',
      results: 'तात्पुरते निकाल',
      setup: 'ऑफलाइन वाक्ये तयार करा',
      offline: 'ऑफलाइन आवाज',
      localVoice: 'उपकरणावरील याच भाषेचा आवाज',
      history: 'बोललेल्या संदेशांचा इतिहास ठेवा',
      vibration: 'कंपन',
      sound: 'निवडलेले शब्द बोला',
      last: 'शेवटचा बोललेला / दाखवलेला संदेश',
      install: 'ऑफलाइन वाक्ये तयार आहेत',
      notReady: 'ऑफलाइन संच तयार नाही. इंटरनेट असताना सेटअप करा.',
      freeze: 'वापरत असताना निकाल स्थिर राहतात.',
      previous: 'मागील',
      next: 'पुढील',
      clear: 'संदेश पुसा',
      language: 'संदेशाची भाषा',
      suggestions: 'पुढील शब्द',
      layout: 'साठवलेली मांडणी',
      legacy: 'सध्याचा बोर्ड',
      large: 'मोठी बटणे',
      text: 'आधी मजकूर',
      preview: 'मांडणी पाहा',
      save: 'मांडणी जतन करा',
      cancel: 'रद्द करा',
      changeLanguage: 'हा संदेश मूळ भाषेत राहील. बदलण्यासाठी त्याची भाषा बदला किंवा नवीन सूचना घ्या.'
    }
  };
  Object.assign(labels.hi, {
    original: 'मूल शब्द',
    requestError: 'सुझाव उपलब्ध नहीं है। अपने शब्द लिखें, दिखाएँ या बोलें।',
    public: 'सार्वजनिक बोर्ड — निजी डेटा के लिए साइन इन करें',
    noAudio: 'आवाज़ उपलब्ध नहीं है। आप सही संदेश दिखा सकते हैं।'
  });
  Object.assign(labels.gu, {
    original: 'મૂળ શબ્દો',
    requestError: 'સૂચન ઉપલબ્ધ નથી. તમારા શબ્દો લખો, બતાવો અથવા બોલો.',
    public: 'જાહેર બોર્ડ — વ્યક્તિગત ડેટા માટે સાઇન ઇન કરો',
    noAudio: 'અવાજ ઉપલબ્ધ નથી. તમે સાચો સંદેશ બતાવી શકો છો.'
  });
  Object.assign(labels.mr, {
    original: 'मूळ शब्द',
    requestError: 'सूचना उपलब्ध नाही. स्वतःचे शब्द लिहा, दाखवा किंवा बोला.',
    public: 'सार्वजनिक बोर्ड — वैयक्तिक माहितीसाठी साइन इन करा',
    noAudio: 'आवाज उपलब्ध नाही. तुम्ही अचूक संदेश दाखवू शकता.'
  });
  labels.en.keyboard = 'On-screen keyboard';
  labels.hi.keyboard = 'स्क्रीन कीबोर्ड';
  labels.gu.keyboard = 'સ્ક્રીન કીબોર્ડ';
  labels.mr.keyboard = 'स्क्रीन कीबोर्ड';
  labels.en.aboutText = 'I am angry about the food.';
  labels.hi.aboutText = 'मुझे खाने पर गुस्सा है।';
  labels.gu.aboutText = 'મને ખોરાક વિશે ગુસ્સો આવે છે.';
  labels.mr.aboutText = 'मला अन्नाबद्दल राग आला आहे.';
  Object.assign(labels.en, {
    speechLoading: 'Preparing speech…',
    speechPlaying: 'Speaking…',
    speechReady: 'Speech ready',
    speechSignIn: 'Sign in to use F5 / IndicF5 speech',
    speechPublic: 'Quick phrases and Show message remain available without signing in.'
  });
  Object.assign(labels.hi, {
    speechLoading: 'आवाज़ तैयार हो रही है…',
    speechPlaying: 'बोल रहे हैं…',
    speechReady: 'आवाज़ तैयार है',
    speechSignIn: 'F5 / IndicF5 आवाज़ के लिए साइन इन करें',
    speechPublic: 'बिना साइन इन भी त्वरित वाक्य और संदेश दिखाना उपलब्ध है।'
  });
  Object.assign(labels.gu, {
    speechLoading: 'અવાજ તૈયાર થઈ રહ્યો છે…',
    speechPlaying: 'બોલી રહ્યું છે…',
    speechReady: 'અવાજ તૈયાર છે',
    speechSignIn: 'F5 / IndicF5 અવાજ માટે સાઇન ઇન કરો',
    speechPublic: 'સાઇન ઇન કર્યા વિના પણ ઝડપી વાક્યો અને સંદેશ બતાવવાનું ઉપલબ્ધ છે.'
  });
  Object.assign(labels.mr, {
    speechLoading: 'आवाज तयार होत आहे…',
    speechPlaying: 'बोलत आहे…',
    speechReady: 'आवाज तयार आहे',
    speechSignIn: 'F5 / IndicF5 आवाजासाठी साइन इन करा',
    speechPublic: 'साइन इन न करताही झटपट वाक्ये आणि संदेश दाखवणे उपलब्ध आहे.'
  });
  Object.assign(labels.en,{makeSentence:'Make sentence',intentContext:'Intent Context:',coreIntent:'Core Intent',selectedContext:'Selected words',flow:'Choose words → Make sentence → Use suggestion → Speak',sentenceBusy:'Making your sentence…',intentRequest:'Requesting',intentFeeling:'Expressing a feeling',intentQuestion:'Asking a question',intentCombined:'Expressing a feeling and making a request',intentSocial:'Social expression',intentUnknown:'More context is needed'});
  Object.assign(labels.hi,{makeSentence:'वाक्य बनाएँ',intentContext:'आशय प्रसंग:',coreIntent:'मुख्य आशय',selectedContext:'चुने शब्द',flow:'शब्द चुनें → वाक्य बनाएँ → सुझाव इस्तेमाल करें → बोलें',sentenceBusy:'आपका वाक्य बन रहा है…',intentRequest:'अनुरोध करना',intentFeeling:'भावना व्यक्त करना',intentQuestion:'प्रश्न पूछना',intentCombined:'भावना और अनुरोध',intentSocial:'सामाजिक अभिव्यक्ति',intentUnknown:'और संदर्भ चाहिए'});
  Object.assign(labels.gu,{makeSentence:'વાક્ય બનાવો',intentContext:'ઉદ્દેશ સંદર્ભ:',coreIntent:'મુખ્ય ઉદ્દેશ',selectedContext:'પસંદ કરેલા શબ્દો',flow:'શબ્દો પસંદ કરો → વાક્ય બનાવો → સૂચન વાપરો → બોલો',sentenceBusy:'તમારું વાક્ય બની રહ્યું છે…',intentRequest:'વિનંતી કરવી',intentFeeling:'લાગણી વ્યક્ત કરવી',intentQuestion:'પ્રશ્ન પૂછવો',intentCombined:'લાગણી અને વિનંતી',intentSocial:'સામાજિક અભિવ્યક્તિ',intentUnknown:'વધુ સંદર્ભ જરૂરી છે'});
  Object.assign(labels.mr,{makeSentence:'वाक्य बनवा',intentContext:'हेतू संदर्भ:',coreIntent:'मुख्य हेतू',selectedContext:'निवडलेले शब्द',flow:'शब्द निवडा → वाक्य बनवा → सूचना वापरा → बोला',sentenceBusy:'तुमचे वाक्य बनत आहे…',intentRequest:'विनंती करणे',intentFeeling:'भावना व्यक्त करणे',intentQuestion:'प्रश्न विचारणे',intentCombined:'भावना आणि विनंती',intentSocial:'सामाजिक अभिव्यक्ती',intentUnknown:'आणखी संदर्भ आवश्यक आहे'});
  const t = k => labels[language]?.[k] || labels.en[k] || k;
  const read = () => {
    try {
      return JSON.parse(localStorage.getItem('aac_access_v1') || '{}');
    } catch (_) {
      return {};
    }
  };
  const [prefs, setPrefs] = useState(read),
    [category, setCategory] = useState('core'),
    [committed, setCommitted] = useState({
      text: '',
      language
    }),
    [preview, setPreview] = useState(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(''),
    [last, setLast] = useState(null),
    [partner, setPartner] = useState(null),
    [act, setAct] = useState('auto'),
    [polarity, setPolarity] = useState('auto'),
    [query, setQuery] = useState(''),
    [predicted, setPredicted] = useState([]),
    [frozen, setFrozen] = useState(null),
    [page, setPage] = useState(0),
    [pack, setPack] = useState(null),
    [installed, setInstalled] = useState(false),
    [layoutPreview, setLayoutPreview] = useState(null),
    [keyboardOpen, setKeyboardOpen] = useState(false),
    [speechStatus, setSpeechStatus] = useState('stopped');
  const revision = useRef(0),
    request = useRef(null),
    undo = useRef([]),
    surface = useRef(null),
    current = useRef({
      profile,
      language
    }),
    capture = useRef(prefs.history !== false);
  current.current = {
    profile,
    language
  };
  capture.current = prefs.history !== false;
  window.AACAccess = prefs;
  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    const update = () => {
      const active = document.activeElement,
        editing = active && ['TEXTAREA', 'INPUT'].includes(active.tagName);
      document.documentElement.dataset.aacKeyboard = editing && viewport.height < window.innerHeight * .8 ? 'open' : 'closed';
      document.documentElement.style.setProperty('--vnext-visual-height', viewport.height + 'px');
      document.documentElement.style.setProperty('--vnext-visual-top', viewport.offsetTop + 'px');
    };
    viewport.addEventListener('resize', update);
    document.addEventListener('focusin', update);
    document.addEventListener('focusout', update);
    return () => {
      viewport.removeEventListener('resize', update);
      document.removeEventListener('focusin', update);
      document.removeEventListener('focusout', update);
    };
  }, []);
  const entries = [...tokens, ...(inputText.trim() ? [{
    label: inputText.trim(),
    cid: null
  }] : [])];
  const analysis = L.analyze(entries, language, act === 'auto' ? null : act);
  const literal = entries.map(x => x.label).join(' '),
    negative = polarity === 'auto' ? analysis.negation : polarity === 'negative';
  const conflict = polarity !== 'auto' && negative !== analysis.negation;
  const layout = prefs.layout || 'legacy';
  const preference = (key, value) => setPrefs(old => {
    const next = {
      ...old,
      [key]: value
    };
    try {
      localStorage.setItem('aac_access_v1', JSON.stringify(next));
    } catch (_) {
      setNotice('Device preferences could not be saved. The working board is unchanged.');
    }
    return next;
  });
  useEffect(() => {
    window.AACPlayback.pack().then(setPack).catch(e => setNotice(e.message));
    window.AACPlayback.readiness().then(setInstalled).catch(() => setInstalled(false));
  }, []);
  useEffect(() => {
    const listener = e => {
      setSpeechStatus(e.detail.status);
      if (e.detail.status === 'playing') {
        setLast(e.detail);
        if (capture.current && e.detail.profile === current.current.profile && e.detail.kind !== 'tile') window.dispatchEvent(new CustomEvent('aac-utterance-start', {
          detail: e.detail
        }));
      }
      if (e.detail.status === 'error') {
        window.AACPlayback.readiness().then(setInstalled);
        setLast({
          text: e.detail.text,
          language: e.detail.language
        });
        setNotice((labels[current.current.language]?.noAudio || labels.en.noAudio) + ' ' + e.detail.message);
      }
    };
    window.addEventListener('aac-playback', listener);
    return () => window.removeEventListener('aac-playback', listener);
  }, []);
  const semanticDraft = JSON.stringify({tokens: tokens.map(item => ({id:item.id, cid:item.cid, label:item.cid ? null : item.label})), text:inputText});
  const priorDraft = useRef(semanticDraft);
  useEffect(() => {
    if (priorDraft.current !== semanticDraft) {
      setCommitted({text:'', language});
      priorDraft.current = semanticDraft;
    }
  }, [semanticDraft]);
  useEffect(() => {
    revision.current++;
    request.current?.abort();
    setPreview(null);
    setBusy(false);
  }, [tokens, inputText, act, polarity, language, profile]);
  const priorProfile = useRef(profile);
  useEffect(() => {
    window.AACPlayback.stop();
    // Initial verification can attach an account to a new public draft without erasing it.
    // Leaving or replacing a verified profile still clears committed private wording.
    if (priorProfile.current) {
      undo.current = [];
      setCommitted({text: '', language});
      setLast(null);
    }
    priorProfile.current = profile;
  }, [profile]);
  useEffect(() => {
    window.AACPlayback.stop();
    setFrozen(null);
    setQuery('');
    setCommitted(old => old.text.trim() ? old : {
      ...old,
      language
    });
  }, [language]);
  useEffect(() => {
    const abort = new AbortController(),
      timeout = setTimeout(() => fetch('/predict_next', {
        method: 'POST',
        signal: abort.signal,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          current_words: tokens.map(x => x.label),
          language
        })
      }).then(r => r.ok ? r.json() : {}).then(data => setPredicted(data.suggestions || [])).catch(() => setPredicted([])), 160);
    return () => {
      clearTimeout(timeout);
      abort.abort();
    };
  }, [tokens, language, profile]);
  useEffect(()=>{if(preview){requestAnimationFrame(()=>{const review=document.getElementById('vnext-sentence-review');review?.focus({preventScroll:true});review?.scrollIntoView({block:'nearest'})})}},[preview]);
  function insertKey(char) {
    remember();
    setInputText(old => old + char);
  }
  function remember() {
    undo.current.push({
      tokens: tokens.map(x => ({
        ...x
      })),
      text: inputText
    });
    if (undo.current.length > 100) undo.current.shift();
  }
  function add(cid, label) {
    remember();
    const item = B[cid];
    setTokens(prev => [...prev, {
      id: crypto.randomUUID(),
      cid: item ? cid : null,
      visualId: item ? cid : null,
      label: label || item[language],
      emoji: item?.emoji || '💬'
    }]);
    if (prefs.vibration && navigator.vibrate) navigator.vibrate(15);
    if (autoPronounce && item) window.AACPlayback.play(label || item[language], language, {
      kind: 'tile',
      rate,
      profile
    });
    onWord?.(label || item?.[language]);
  }
  function commit(text, lg = language) {
    setCommitted({
      text,
      language: lg
    });
    setNotice('');
    requestAnimationFrame(() => document.getElementById('vnext-ready')?.scrollIntoView({
      block: 'nearest'
    }));
  }
  function undoDraft() {
    const prev = undo.current.pop();
    if (prev) {
      setTokens(prev.tokens.map(token => token.cid ? {
        ...token,
        label: B[token.cid]?.[language] || token.label
      } : token));
      setInputText(prev.text);
    }
  }
  function stop() {
    window.AACPlayback.stop();
    setSpeechStatus('stopped');
    revision.current++;
    request.current?.abort();
    setBusy(false);
  }
  function explicitSpeak() {
    const text = (committed.text || literal).trim();
    const targetLanguage = committed.text.trim() ? committed.language : language;
    if (!text) { setNotice(t('typed')); return; }
    // The visible ready field previews the exact draft. Pressing Speak is the explicit commit.
    setCommitted({text, language: targetLanguage});
    window.AACPlayback.play(text, targetLanguage, {kind: 'message', rate, profile});
  }

  async function quick(key) {
    request.current?.abort();
    revision.current++;
    setBusy(false);
    const phrase = pack?.phrases.find(x => x.key === key && x.language === language);
    if (!phrase) return;
    setLast(phrase);
    setNotice('');
    await window.AACPlayback.play(phrase.text, language, {
      quick: key,
      kind: 'quick',
      rate,
      profile
    });
  }
  async function polish(forced) {
    request.current?.abort();
    const ticket = ++revision.current,
      owner = profile,
      lg = language;
    if (analysis.n_negators > 1 && polarity === 'auto') {
      setPreview({
        outcome: 'clarification',
        reason: 'repeat'
      });
      return;
    }
    if (analysis.angryFood && !forced && act === 'auto') {
      setPreview({
        outcome: 'clarification',
        reason: 'angry'
      });
      return;
    }
    if (entries.length === 1 && entries[0].cid === 'NO') {
      setPreview({
        outcome: 'literal_preview',
        text: literal
      });
      return;
    }
    setBusy(true);
    setPreview(null);
    request.current = new AbortController();
    try {
      const payload = {
        entities: entries.map(x => x.label),
        concept_ids: entries.map(x => x.cid || null),
        act: forced || (analysis.act === 'UNKNOWN' && polarity !== 'auto' ? L.analyze(entries.filter(x => x.cid !== 'NO' && !['no', 'not', 'नहीं', 'नही', 'ना', 'ના', 'नाही', 'नको'].includes(L.norm(x.label))), language).act : analysis.act),
        act_source: forced || act !== 'auto' || polarity !== 'auto' ? 'user' : 'client',
        negation: negative,
        polarity: negative ? 'negative' : 'positive',
        language: lg,
        include_audio: false,
        generation_mode: 'dual'
      };
      const r = await fetch('/generate', {
        method: 'POST',
        credentials: 'same-origin',
        signal: request.current.signal,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      if (ticket !== revision.current || current.current.profile !== owner || current.current.language !== lg) return;
      if (!r.ok) throw Error(typeof data.detail === 'string' ? data.detail : t('requestError'));
      setPreview({
        ...data,
        revision: ticket,
        language: lg
      });
    } catch (e) {
      if (ticket === revision.current && e.name !== 'AbortError') {
        setPreview({
          outcome: 'failure'
        });
        setNotice(t('requestError'));
      }
    } finally {
      if (ticket === revision.current) setBusy(false);
    }
  }
  const found = query.trim() ? Object.keys(B).filter(cid => Object.values(B[cid]).some(value => typeof value === 'string' && value.toLowerCase().includes(query.toLowerCase()))).map(cid => ({
    cid,
    label: B[cid][language]
  })) : predicted.map(x => ({
    cid: null,
    label: x.word
  }));
  const results = frozen || found;
  function regionExit(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) setFrozen(null);
  }
  function spatial(e) {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) return;
    const nodes = [...e.currentTarget.querySelectorAll('button[data-slot-id]')],
      index = nodes.indexOf(document.activeElement);
    if (index < 0) return;
    let next = index;
    if (e.key === 'Home') next = 0;else if (e.key === 'End') next = nodes.length - 1;else {
      const r = nodes[index].getBoundingClientRect();
      const candidates = nodes.map((n, i) => ({
        i,
        r: n.getBoundingClientRect()
      })).filter(x => e.key === 'ArrowRight' ? x.r.x > r.x && Math.abs(x.r.y - r.y) < 5 : e.key === 'ArrowLeft' ? x.r.x < r.x && Math.abs(x.r.y - r.y) < 5 : e.key === 'ArrowDown' ? x.r.y > r.y : e.key === 'ArrowUp' ? x.r.y < r.y : false);
      candidates.sort((a, b) => Math.abs(a.r.y - r.y) * 2 + Math.abs(a.r.x - r.x) - (Math.abs(b.r.y - r.y) * 2 + Math.abs(b.r.x - r.x)));
      if (candidates.length) next = candidates[0].i;
    }
    e.preventDefault();
    nodes[next]?.focus();
  }
  const nativeDialog = (title, body, close) => <div className="vnext-overlay" onPointerDown={e => {
    if (e.target === e.currentTarget) close();
  }}><section className="vnext-dialog" role="dialog" aria-modal="true" aria-label={title} ref={node => {
      if (node && !node.dataset.focused) {
        node.dataset.focused = '1';
        setTimeout(() => node.querySelector('button')?.focus(), 0);
      }
    }} onKeyDown={e => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        close();
      }
      if (e.key === 'Tab') {
        const nodes = [...e.currentTarget.querySelectorAll('button,input,textarea,select')].filter(n => !n.disabled),
          first = nodes[0],
          last = nodes.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }}><header><h2>{title}</h2><button type="button" onClick={close}>{t('close')}</button></header>{body}</section></div>;
  const closePartner = () => {
    setPartner(null);
    setTimeout(() => document.getElementById('vnext-show')?.focus(), 0);
  };
  return <main className="vnext" ref={surface} data-layout={layout}>
  <section className="vnext-quick" aria-label="Quick Express">{['help', 'water', 'bathroom', 'pain'].map((key, index) => <button type="button" key={key} data-quick={key} onClick={() => quick(key)}><span aria-hidden="true">{['🆘', '💧', '🚻', '🤕'][index]}</span><strong>{t(key)}</strong></button>)}</section>
  <section className="vnext-message" aria-label={t('draft')}>
   <div className="vnext-speech-actions"><button id="vnext-speak" className="vnext-primary" type="button" disabled={!(committed.text || literal).trim()} aria-busy={speechStatus === 'loading'} onClick={explicitSpeak}>{t('speak')}</button><button type="button" id="vnext-polish" title={t('polish')} disabled={busy || !literal.trim()} onClick={() => polish()}>{busy ? t('sentenceBusy') : t('makeSentence')}</button><button id="vnext-stop" type="button" onClick={stop}>{t('stop')}</button><button id="vnext-show" type="button" disabled={!committed.text.trim() && !literal.trim()} onClick={() => setPartner({
          text: committed.text || literal,
          language: committed.text ? committed.language : language
        })}>{t('show')}</button></div>
   <p className="vnext-speech-status" role="status" aria-live="polite">{speechStatus === 'loading' ? t('speechLoading') : speechStatus === 'playing' ? t('speechPlaying') : t('speechReady')} · {committed.language === 'en' ? 'F5-TTS' : 'IndicF5'} · {committed.language}</p>
   {!profile && <div className="vnext-sign-in"><a href="/login">{t('speechSignIn')}</a><p>{t('speechPublic')}</p></div>}
   <div hidden className="vnext-intent-context" id="vnext-intent-context" role="status" aria-live="polite"><strong>{t('intentContext')}</strong>{' '}<span><b>{t('coreIntent')}:</b>{' '}{negative?t('refusal'):t(({REQUEST:'intentRequest',FEELING:'intentFeeling',FEELING_REQUEST:'intentCombined',QUESTION:'intentQuestion',GREETING:'intentSocial'})[analysis.act]||'intentUnknown')}{literal&&<>{' — '}{t('selectedContext')}: {literal}</>}</span></div>
   <p hidden className="vnext-flow">{t('flow')}</p>
   <header><h1>{t('draft')}</h1><span className="vnext-state">{negative ? t('refusal') : t(analysis.act)}</span></header>
   <label htmlFor="vnext-ready">{t('ready')}</label><textarea id="vnext-ready" rows="2" lang={committed.language} value={committed.text || literal} onChange={e => commit(e.target.value, committed.text.trim() ? committed.language : language)} />
   <label hidden className="vnext-message-language">{t('language')}<select id="vnext-message-language" value={committed.language} onChange={e => commit(committed.text, e.target.value)}>{L.langs.map(lg => <option key={lg} value={lg}>{{
              en: 'English',
              hi: 'हिन्दी',
              gu: 'ગુજરાતી',
              mr: 'मराठी'
            }[lg]}</option>)}</select></label>
   {committed.language !== language && <p>{t('changeLanguage')}</p>}

   <div className="vnext-selected" aria-label={t('words')}>{tokens.map(token => <span key={token.id} className="vnext-token">{token.label}</span>)}</div>
   <label htmlFor="vnext-draft">{t('typed')}</label><textarea id="vnext-draft" rows="2" value={inputText} onFocus={remember} onChange={e => {
        remember();
        setInputText(e.target.value);
      }} />
   <div className="vnext-row"><button type="button" onClick={() => commit(tokens.map(x => x.label).join(' '))} disabled={!tokens.length}>{t('words')}</button><button type="button" onClick={() => commit(inputText)} disabled={!inputText.trim()}>{t('useTyped')}</button>{keyboard && <button type="button" id="vnext-keyboard-open" onClick={() => setKeyboardOpen(true)}>{t('keyboard')}</button>}<button type="button" onClick={undoDraft} disabled={!undo.current.length}>{t('undo')}</button><button type="button" onClick={() => {
          remember();
          setTokens([]);
          setInputText('');
        }}>{t('clear')}</button></div>
   <div hidden className="vnext-row vnext-intent"><label>{t('act')}<select id="vnext-act" value={act} onChange={e => setAct(e.target.value)}>{['auto', 'REQUEST', 'FEELING', 'FEELING_REQUEST', 'QUESTION', 'GREETING'].map(x => <option key={x} value={x}>{t(x)}</option>)}</select></label><label>{t('polarity')}<select id="vnext-polarity" value={polarity} onChange={e => setPolarity(e.target.value)}>{['auto', 'positive', 'negative'].map(x => <option key={x} value={x}>{t(x)}</option>)}</select></label></div>
   {conflict && <p role="status">{t('conflict')}</p>}
   {preview && <section className="vnext-review" id="vnext-sentence-review" tabIndex={-1} aria-label={t('suggestion')}><strong>{t('suggestion')}</strong><p><strong>{t('original')}: </strong>{literal}</p>{preview.outcome === 'clarification' ? <><p>{t(preview.reason === 'repeat' ? 'repeat' : preview.reason === 'angry' ? 'angry' : 'clarify')}</p>{preview.reason === 'angry' ? <><button type="button" onClick={() => {
              commit(t('aboutText'));
              setPreview(null);
            }}>{t('about')}</button><button type="button" onClick={() => {
              polish('FEELING_REQUEST');
            }}>{t('both')}</button></> : <><button type="button" onClick={() => {
              polish('REQUEST');
            }}>{t('REQUEST')}</button><button type="button" onClick={() => {
              polish('FEELING');
            }}>{t('FEELING')}</button></>}</> : L.eligible(preview) ? <><p lang={preview.language}>{preview.text}</p><button type="button" id="vnext-use-suggestion" onClick={() => {
            commit(preview.text, preview.language);
            setPreview(null);
          }}>{t('use')}</button></> : <><p>{t('literal')}</p><p>{literal}</p></>}</section>}
   {notice && <p className="vnext-notice" role="status">{notice}</p>}
   {last && <div hidden className="vnext-last"><strong>{t('last')}</strong><p lang={last.language}>{last.text}</p><button type="button" onClick={() => setPartner(last)}>{t('show')}</button><button type="button" onClick={() => window.AACPlayback.localVoice(last.text, last.language, {
          rate,
          profile
        })}>{t('localVoice')}</button></div>}
  </section>
  <section className="vnext-vocabulary" aria-label={t('home')}>
   <nav className="vnext-categories" aria-label={t('home')}><button type="button" className="vnext-home" onClick={() => setCategory('core')}>{t('home')}</button>{['core', 'actions', 'food', 'feelings', 'people', 'places', 'body', 'chat', 'emergency'].map(cat => <button type="button" key={cat} aria-pressed={category === cat} data-category={cat} onClick={() => {
          setCategory(cat);
          setPage(0);
        }}>{t(cat)}</button>)}</nav>
   <div className="vnext-board" onKeyDown={spatial} data-board-layout={layout}>{L.slots(category).map(({
          cid,
          slot
        }) => cid ? <button type="button" key={slot} data-slot-id={slot} data-concept-id={cid} data-symbol-id={cid} className={Object.values(L.anchors).includes(cid) ? 'vnext-anchor' : ''} onClick={() => add(cid)}>{layout !== 'text' && renderSymbol({
            k: cid,
            e: B[cid].emoji,
            labels: Object.fromEntries(L.langs.map(lg => [lg, B[cid][lg]]))
          })}<span>{B[cid][language]}</span>{Object.values(L.anchors).includes(cid) && <small aria-hidden="true">●</small>}</button> : <span className="vnext-empty-slot" key={slot} aria-hidden="true" />)}</div>
   <section className="vnext-results" aria-label={t('results')} onFocusCapture={() => {
        if (!frozen) setFrozen(found);
      }} onBlurCapture={regionExit} onPointerEnter={() => {
        if (!frozen) setFrozen(found);
      }} onPointerLeave={e => {
        if (!e.currentTarget.contains(document.activeElement)) setFrozen(null);
      }}>
    <label htmlFor="vnext-search">{t('search')}</label><input id="vnext-search" type="search" value={query} onChange={e => {
          setQuery(e.target.value);
          if (!surface.current?.querySelector('.vnext-results')?.contains(document.activeElement) || document.activeElement.id === 'vnext-search') setFrozen(null);
        }} />
    <div className="vnext-result-ribbon">{results.map((x, i) => <button type="button" key={x.cid || x.label + '-' + i} onClick={() => add(x.cid, x.label)}>{x.label}</button>)}</div><small>{t('freeze')}</small>
   </section>
   <details className="vnext-settings"><summary>{t('offline')} · {t('layout')}</summary><div className="vnext-settings-body"><p>{installed ? t('install') : t('notReady')}</p><button type="button" onClick={async () => {
            try {
              setNotice(t('setup') + '…');
              await window.AACPlayback.provision();
              setInstalled(true);
              setNotice(t('install'));
            } catch (e) {
              setNotice(e.message);
            }
          }}>{t('setup')}</button>
    <label><input type="checkbox" checked={prefs.history !== false} onChange={e => preference('history', e.target.checked)} />{t('history')}</label><label><input type="checkbox" checked={!!prefs.vibration} onChange={e => preference('vibration', e.target.checked)} />{t('vibration')}</label><label><input type="checkbox" checked={autoPronounce} onChange={e => onSoundChange(e.target.checked)} />{t('sound')}</label>
    <label>{t('layout')}<select value={layout} id="vnext-layout" onChange={e => setLayoutPreview(e.target.value)}>{['legacy', 'large', 'text'].map(l => <option key={l} value={l}>{t(l)}</option>)}</select></label>{!profile && <p>{t('public')}</p>}{support}
   </div></details>
  </section>
  {keyboardOpen && nativeDialog(t('keyboard'), <><label htmlFor="vnext-keyboard-input">{t('typed')}</label><textarea id="vnext-keyboard-input" value={inputText} onChange={e => {
        remember();
        setInputText(e.target.value);
      }} /><div className="vnext-row"><button type="button" onClick={() => commit(inputText)}>{t('useTyped')}</button><button type="button" onClick={explicitSpeak} disabled={!(committed.text || literal).trim()}>{t('speak')}</button><button type="button" onClick={stop}>{t('stop')}</button></div><p lang={committed.language}>{committed.text}</p><div className="vnext-keyboard-grid">{[...(keyboard?.vowels || []), ...(keyboard?.consonants || []).flat(), ...(keyboard?.matras || [])].map((item, i) => {
          const char = typeof item === 'string' ? item : item.char;
          return <button type="button" key={i} onClick={() => insertKey(char)}>{char}</button>;
        })}<button type="button" aria-label="Space" onClick={() => insertKey(' ')}>␣</button><button type="button" aria-label={t('undo')} onClick={undoDraft}>↶</button></div></>, () => {
      setKeyboardOpen(false);
      setTimeout(() => document.getElementById('vnext-keyboard-open')?.focus(), 0);
    })}
  {partner && nativeDialog(t('show'), <p className="vnext-partner-message" lang={partner.language}>{partner.text}</p>, closePartner)}
  {layoutPreview && nativeDialog(t('preview'), <><div className="vnext-layout-sample" data-layout={layoutPreview}>{Object.values(L.anchors).map(id => <span key={id}>{B[id][language]}</span>)}</div><button type="button" onClick={() => {
        preference('layout', layoutPreview);
        setLayoutPreview(null);
        setTimeout(() => document.getElementById('vnext-layout')?.focus(), 0);
      }}>{t('save')}</button><button type="button" onClick={() => {
        setLayoutPreview(null);
        setTimeout(() => document.getElementById('vnext-layout')?.focus(), 0);
      }}>{t('cancel')}</button></>, () => {
      setLayoutPreview(null);
      setTimeout(() => document.getElementById('vnext-layout')?.focus(), 0);
    })}
 </main>;
};
