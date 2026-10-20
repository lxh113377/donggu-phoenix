/* ar-data.js — AR 展陈三场景内容源（与 culture.js 同为唯一内容源，禁止在渲染层写死文案）
 * 事实来源标注在每个章节的 source 字段，来源链接只在「资料来源」区展示，页面不发任何外部请求。
 * 工序名目依据：刘卷《东固传统造像的制作工艺与仪式过程及其文化功能阐释》，《装饰》2015 年第 7 期；
 * 非遗与开光说明：吉安市人民政府《东固传统造像》专题页（2014 年第四批国家级非遗代表性项目）。
 * 红色史实依据：人民网党史频道转载《江西日报》2021-08-06《赣水那边红一角》。
 * 凤凰装依据：福建省文物局《文物里的福丨畲族"凤凰装"》。
 */
window.AR_DATA = {
  meta: {
    title: 'AR 展陈馆',
    en: 'Lightweight AR Gallery',
    /* 轻量化口径：三个场景全部为 Canvas 2D 实时绘制，零模型文件、零第三方库、零外部请求 */
    /* 停留时长为按分镜时长 + 每章阅读时长做的设计估算，尚未做现场实测，勿当作实测数据 */
    dwell: '加读解说与集章，设计目标停留约 4–6 分钟（估算，非实测）'
  },

  /* 三段动线：扫 → 叠加 → 集章 */
  route: [
    { step: '01', title: '扫码进入', en: 'Scan', desc: '展板、文创、门票上的二维码指向本页；也可在页内直接唤起' },
    { step: '02', title: '现实叠加', en: 'Overlay', desc: '摄像头取景为底，技艺流程与历史场景以半透明图层叠加在真实造像、地标之上' },
    { step: '03', title: '看完集章', en: 'Stamp', desc: '每段结束落一枚印章，三枚集齐即解锁完整动线' }
  ],

  scenes: [
    /* ============ 场景一：东固传统造像 ============ */
    {
      id: 'craft',
      no: '01',
      name: '东固传统造像',
      en: 'Donggu Traditional Statuary',
      kicker: '国家级非物质文化遗产 · 2014 年入选第四批名录',
      tagline: '一木成像：拖动进度，看这段樟木里的神像被让出来',
      duration: 72,
      poster: 50,
      stamp: '造像章',
      chapters: [
        {
          at: 0, key: 'wood', title: '一 · 选木', en: 'I. Choosing the Wood',
          body: '造像先看木。东固一带用樟木：整段要干透、无裂、少节，顺纹理立身，取直去斜。木性稳了，像才立得住。',
          enBody: 'It starts with the wood — camphor, thoroughly seasoned, free of cracks and large knots, stood upright along the grain.',
          note: '工序名目据《装饰》2015 年第 7 期田野调查；樟木用料据《井冈山报》2026-08-10'
        },
        {
          at: 12, key: 'design', title: '二 · 定像', en: 'II. Fixing the Iconography',
          body: '丹青先生依信众所求定尊格、量体量、起稿放样：先立中轴，再分头、胸、腰、膝的比例，粉线一弹，尺寸就定死在木上。',
          enBody: 'The master fixes the deity, measures the image and lays out the draft: a central axis first, then the proportions of head, chest, waist and knee.',
          note: '「丹青先生」称谓见吉安市人民政府专题页'
        },
        {
          at: 24, key: 'block', title: '三 · 开坯', en: 'III. Blocking Out',
          body: '斧锯开大形，凿子打坯。先方后圆、先粗后细，一层层把多余的木头让出去——这一步错一寸，后面全要跟着错。',
          enBody: 'Axes and saws rough out the mass; chisels block it in. Square first, then round; coarse first, then fine.',
          note: '开坯为《装饰》所列工序'
        },
        {
          at: 40, key: 'gild', title: '四 · 修光 · 彩绘 · 贴金', en: 'IV. Refining, Painting, Gilding',
          body: '修光打磨，把刀痕收干净；生漆打底，再上彩、贴金箔。眉眼的弧度、衣纹的走向，都在这时候定下神情。',
          enBody: 'Sanding removes every chisel mark, then the face is opened — awe without terror, kinship without vulgarity. Lacquer, pigment and gold leaf follow.',
          note: '贴金为《装饰》所列工序；「开面」分寸见《井冈山报》2026-08-10《樟木深处听刀音》'
        },
        {
          at: 56, key: 'open', title: '五 · 开光', en: 'V. Consecration',
          body: '神像雕成，还不算完成。丹青先生要亲自主持一系列复杂的「开光仪式」，通过仪式赋予那些「木头」神像「法力」，至此造像工作才宣告完成。',
          enBody: 'A carved image is not yet a deity. The master presides over the consecration rite itself, endowing the wooden figure with power — only then is the work finished.',
          note: '开光仪式表述引自吉安市人民政府专题页原文'
        }
      ],
      sources: [
        { label: '刘卷《东固传统造像的制作工艺与仪式过程及其文化功能阐释》，《装饰》2015 年第 7 期', url: 'https://wap.cnki.net/touch/web/Journal/Article/ZSHI201507026.html' },
        { label: '吉安市人民政府《东固传统造像》', url: 'https://m.jian.gov.cn/news-show-9917.html' },
        { label: '刘节明先生独家专访实录（团队 2025-07-07 田野采访）', url: '' },
        { label: '《井冈山报》2026-08-10《樟木深处听刀音——记国家级非遗项目东固传统造像代表性传承人刘节明》', url: 'https://www.jgsdaily.com/19/19qysj/19tt/145190.shtml' }
      ]
    },

    /* ============ 场景二：红色地标 ============ */
    {
      id: 'red',
      no: '02',
      name: '红色地标 · 历史场景复原',
      en: 'Red Landmarks · Historical Reconstruction',
      kicker: '东固革命根据地 · 1929—1931',
      tagline: '把「东井冈」的四年，压缩成四段可叠加的现场',
      duration: 44,
      poster: 3,
      stamp: '会师章',
      chapters: [
        {
          at: 0, key: 'meet', title: '一九二九 · 东固会师', en: '1929 · The Donggu Rendezvous',
          body: '1929 年 2 月，毛泽东、朱德率红四军转战赣南，来到东固革命根据地，举行了著名的「东固会师」。陈毅后来把这里称作「东井冈」。',
          enBody: 'In February 1929, Mao Zedong and Zhu De led the Fourth Red Army south into Jiangxi and met the Donggu base forces — the rendezvous that earned Donggu the name “East Jinggangshan”.',
          note: '《江西日报》2021-08-06'
        },
        {
          at: 11, key: 'longgang', title: '一九三〇 · 龙冈大捷', en: '1930 · Victory at Longgang',
          body: '第一次反「围剿」，张辉瓒部被诱入龙冈的「布袋」。红军全歼敌十八师。毛泽东写下《渔家傲》：雾满龙冈千嶂暗，齐声唤，前头捉了张辉瓒。',
          enBody: 'In the first counter-encirclement campaign, Zhang Huizan’s 18th Division was lured into the “cloth bag” at Longgang and wiped out. Mao Zedong wrote in his poem “Pride of Fisherman”: ‘Mist veils Longgang, a thousand peaks in gloom; all cry out — Zhang Huizan is taken at the front.’',
          note: '《江西日报》2021-08-06'
        },
        {
          at: 22, key: 'baiyun', title: '一九三一 · 白云山首战', en: '1931 · First Battle at Baiyun Mountain',
          body: '第二次反「围剿」首战，毛泽东、朱德在白云山前的小山村设指挥所，与敌遭遇；红军主力自山上压向敌人，一举歼敌七千余人。「白云山头云欲立」。',
          enBody: 'The opening battle of the second counter-encirclement: Mao Zedong and Zhu De set their command post in a hamlet before Baiyun Mountain and met the enemy head-on; the main Red Army force swept down from the ridge and destroyed over seven thousand of them. ‘Clouds rise over Baiyun’s peak.’',
          note: '《江西日报》2021-08-06'
        },
        {
          at: 33, key: 'huang', title: '一九三一 · 六渡坳', en: '1931 · Liudu’ao',
          body: '1931 年 9 月 15 日，红三军军长黄公略在六渡坳遭敌机扫射牺牲，年仅 33 岁。临终他说：就把我埋在东固，我喜欢这里的人民，喜欢这里的山和水。',
          enBody: 'On 15 September 1931, Huang Gonglue, commander of the Third Red Army, was killed by strafing aircraft at Liudu’ao. He was 33. His last words: ‘Bury me in Donggu — I love its people, I love its mountains and its waters.’',
          note: '《江西日报》2021-08-06'
        }
      ],
      sources: [
        { label: '《江西日报》2021-08-06《赣水那边红一角》，人民网党史频道转载', url: 'http://dangshi.people.com.cn/BIG5/n1/2021/0806/c436975-32183983.html' },
        { label: '东固革命根据地博物馆公开资料（旧址群：平民银行、毛泽东旧居、会师广场等）', url: '' }
      ]
    },

    /* ============ 场景三：畲族凤凰图腾 ============ */
    {
      id: 'phoenix',
      no: '03',
      name: '畲族凤凰图腾',
      en: 'She Phoenix Totem',
      kicker: '畲族凤凰装 · 三公主的羽衣',
      tagline: '一枚图腾，三种凤凰装，一只会盘旋的凤凰',
      duration: 36,
      poster: 16,
      stamp: '凤凰章',
      chapters: [
        {
          at: 0, key: 'totem', title: '图腾浮现', en: 'The Totem Appears',
          body: '畲族没有本民族的文字，纹样便是经卷。这枚图腾以凤凰装为骨：凤髻为冠、花边为翼、金腰带作尾羽、银器化星点。',
          enBody: 'Without a written script of their own, the She people kept their chronicle in patterns: a phoenix-hair bun as crown, embroidered borders as wings, a golden belt as tail.',
          note: '福建省文物局《畲族「凤凰装」》'
        },
        {
          at: 9, key: 'princess', title: '三公主的羽衣', en: 'The Third Princess’s Robe',
          body: '传说盘瓠因平番有功，被高辛帝招为东床快婿；成婚那日，三公主凤冠凤衣。此后畲家生女，便备一身凤凰装。',
          enBody: 'Legend tells of the Third Princess wed in phoenix crown and robe; ever after, every She daughter was dressed as a phoenix.',
          note: '福建省文物局《畲族「凤凰装」》'
        },
        {
          at: 18, key: 'flight', title: '振翅与盘旋', en: 'Wings and Circles',
          body: '凤凰装随年龄分大、小、老三式，样式相同而繁简有别。三式只有年龄与地域之别，没有等级贵贱——每一位畲族女性，都被视作三公主的化身。',
          enBody: 'The phoenix costume comes in three forms — great, small and elder — alike in cut, differing only in richness. The three differ by age and region, never by rank: every She woman is held to be an incarnation of the Third Princess.',
          note: '福建省文物局《畲族「凤凰装」》'
        },
        {
          at: 27, key: 'settle', title: '落羽归位', en: 'Feathers Settle',
          body: '红头绳、金丝银线、后腰的金黄腰带随风飘曳，是凤凰的尾羽；周身银器叮当，是凤凰的鸣啭。山歌一开口，凤凰就落在东固。',
          enBody: 'Red cord, gold thread, a golden sash trailing like tail feathers, silver ornaments chiming like birdsong — the moment a mountain song begins, the phoenix alights on Donggu.',
          note: '福建省文物局《畲族「凤凰装」》'
        }
      ],
      sources: [
        { label: '福建省文物局《文物里的福丨畲族「凤凰装」》', url: '' },
        { label: '东固畲族乡田野采访与团队实拍素材', url: '' }
      ]
    }
  ],

  /* 凤凰装三式配色（取自凤凰装实色描述） */
  costumes: [
    { id: 'great', name: '大凤凰装', en: 'Great Phoenix', note: '纹样最繁，红多金重' },
    { id: 'small', name: '小凤凰装', en: 'Small Phoenix', note: '样式相同，更简约' },
    { id: 'elder', name: '老凤凰装', en: 'Elder Phoenix', note: '头髻较低，纹样沉稳' }
  ],

  ui: {
    scanHint: '把造像或地标放进取景框中央',
    scanHintAdd: '对准后自动叠加，也可直接开演',
    skip: '直接开演',
    locked: '已锁定 · 开始叠加',
    displayMode: '展柜模式',
    camMode: '实景叠加',
    prev: '上一段',
    next: '下一段',
    play: '暂停',
    pause: '继续',
    restart: '重播',
    done: '本段完成 · 已落章',
    stampNew: '新落一章',
    stamps: '集章',
    total: '本页 AR 已停留',
    noCam: '没有可用摄像头，已切到展柜模式',
    tapScene: '轻触场景卡片开演'
  }
};