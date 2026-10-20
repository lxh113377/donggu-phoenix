/* culture.js — 站点唯一内容源。文案全部取自「素材/」内实拍采访稿与已核实的公开资料，禁止改写史实。 */
window.CULTURE = {
  meta: {
    title: '畲 · 凤鸣东固',
    subtitle: '扫描畲族凤凰图腾 · 见凤凰起舞',
    team: '江西科技学院 · 薪火寰行实践团',
    place: '江西省吉安市青原区东固畲族乡',
    year: '2025'
  },

  hero: {
    line1: '畲',
    line2: '凤鸣东固',
    tag: '国家级非物质文化遗产 · 东固传统造像 AR 数字展陈',
    lead: '一枚图腾，一只凤凰。\n扫描它，让三百年前的羽衣在屏幕上重新张开。',
    cta: '轻触图腾 · 唤凤'
  },

  /* 文化段落：依据「畲族凤凰装」公开文物资料与东固畲族乡田野采访整理 */
  culture: [
    {
      id: 'princess',
      no: '01',
      title: '三公主的羽衣',
      kicker: '起源',
      body: '畲族奉盘瓠为始祖。传说盘瓠因平番有功，被高辛帝招为东床快婿；成婚那日，三公主凤冠凤衣、光彩照人。婚后她照着自己出嫁时的模样为女儿装扮，从此畲家生女，便备一身凤凰装。',
      notes: ['盘瓠传说 · 三公主', '凤冠凤衣之始']
    },
    {
      id: 'costume',
      no: '02',
      title: '凤髻 · 花边 · 金腰带',
      kicker: '形制',
      body: '红头绳扎髻高盘于顶，称凤髻；衣裙绣大红、桃红夹黄的花边，镶金丝银线，象征凤凰的颈、腰与羽毛；后腰金黄的腰带随风飘曳，是凤凰的尾羽；周身银器叮当，是凤凰的鸣啭。',
      notes: ['凤髻', '金丝银线', '银饰鸣啭']
    },
    {
      id: 'ages',
      no: '03',
      title: '大凤凰 · 小凤凰 · 老凤凰',
      kicker: '一生',
      body: '凤凰装随年龄分大、小、老三式：未成年女子着「小凤凰装」，样式相同而更简约；老年妇女着「老凤凰装」，头髻较低、纹样沉稳。三式只有年龄与地域之别，没有等级贵贱——每一位畲族女性，都被视作三公主的化身。',
      notes: ['无等级之别', '女性地位']
    },
    {
      id: 'donggu',
      no: '04',
      title: '东固 · 山歌与乌饭',
      kicker: '在地',
      body: '东固畲族乡位于江西吉安青原区。畲族有语言而无本民族文字，历史与情感都靠山歌口耳相传；三月三乌饭节，则以乌稔叶染米，蒸出一锅墨色的春天。',
      notes: ['畲歌口传', '三月三 · 乌饭节']
    }
  ],

  /* 匠人：逐字取自 素材/东固传统造像传承人采访稿.docx 与 素材/畲族党员采访稿.docx */
  craftsmen: [
    {
      id: 'liu',
      name: '刘节明',
      role: '东固传统造像 · 省级非遗传承人',
      avatar: 'assets/img/photos/craft-liu.webp',
      quote: '我们这一脉自始至终都以传承技艺为核心。',
      blocks: [
        { k: '来历', v: '祖上隶属「雕銮匠」，在南京参与皇宫建造，朝廷赐下半副銮驾。' },
        { k: '学艺', v: '那时纸张奢侈，把香烟的烟纸拆开用；探矿队给的几张好纸，不舍得用。' },
        { k: '创新', v: '从宗教造像，到革命时期家具造像，再到融入本地红色文化。' },
        { k: '传承', v: '国家有要求，不光教儿子，还带徒弟，特别带了好几个女弟子。' }
      ]
    },
    {
      id: 'lei',
      name: '雷爷爷',
      role: '东固畲族乡 · 畲族党员 · 38 年党龄',
      avatar: 'assets/img/photos/craft-lei.webp',
      quote: '没有共产党，就没有我们现在的好生活。',
      blocks: [
        { k: '入党', v: '1987 年入党。王进喜、龚全珍、焦裕禄的事迹，让他下定决心。' },
        { k: '任职', v: '1973 年任大队民兵连长，1980 年起任大队会计，一直干到 2005 年。' },
        { k: '初心', v: '印象最深的，是帮村民解决生活里的困难。' },
        { k: '寄语', v: '年轻人一定要不忘初心、牢记使命，要勇于向上。' }
      ]
    }
  ],

  /* 文创：规格沿用 素材/ 内手绘草图实测尺寸 */
  merch: [
    { id: 'badge', image: 'assets/img/merch/r-badge.webp', name: '凤凰徽章',   spec: 'Ø 58 mm · 马口铁包边 + 安全别针', tier: '现有延续',
      desc: '沿用实践团现有徽章工艺，图腾取单色线描版，适合批量发放。' },
    { id: 'pen', image: 'assets/img/merch/r-pen.webp', name: '凤羽笔筒',   spec: '80 × 80 × 110 mm · 榉木 / 亚克力双版', tier: '现有延续',
      desc: '四面分别刻图腾、凤髻、金腰带与银饰四段纹样。' },
    { id: 'note', image: 'assets/img/merch/r-note.webp', name: '凤鸣笔记本', spec: '145 × 212 mm · 硬壳锁线 · 100g 米白内页', tier: '现有延续',
      desc: '封面压印图腾烫金，内页附畲族凤凰装形制图解。' },
    { id: 'lamp', image: 'assets/img/merch/r-lamp.webp', name: '凤影纸雕灯', spec: '210 × 91 mm · 七层激光镂空 · 暖白 3000K', tier: '现有延续',
      desc: '分层叠影：底层山峦、中层凤凰、顶层圆光，开灯即见凤舞。' },
    { id: 'fan', image: 'assets/img/merch/r-fan.webp', name: '凤凰团扇',   spec: 'Ø 210 mm · 绢面 + 竹柄', tier: '现有延续',
      desc: '扇面取「振翅回望」构图，留白题「凤鸣东固」。' },
    { id: 'magnet', image: 'assets/img/merch/r-magnet.webp', name: '凤凰冰箱贴', spec: '60 × 60 mm · 软磁 + 滴胶', tier: '高频低成本',
      desc: '现场发放首选，三个配色对应大、小、老凤凰装。' },
    { id: 'bookmark', image: 'assets/img/merch/r-bookmark.webp', name: '凤羽书签', spec: '40 × 150 mm · 黄铜蚀刻', tier: '高频低成本',
      desc: '以单支尾羽为形，蚀刻畲族织带纹。' },
    { id: 'postcard', image: 'assets/img/merch/r-postcard.webp', name: 'AR 明信片', spec: '148 × 100 mm · 双面四色', tier: '数字衍生',
      desc: '正面印图腾，扫码即见凤凰飞舞，可寄可藏。' },
    { id: 'tote', image: 'assets/img/merch/r-tote.webp', name: '凤纹帆布袋', spec: '380 × 420 mm · 12oz 本白棉', tier: '高客单',
      desc: '丝网印三色图腾，肩带织带纹样呼应凤凰装花边。' },
    { id: 'scarf', image: 'assets/img/merch/r-scarf.webp', name: '凤羽丝巾',   spec: '900 × 900 mm · 桑蚕丝 12 姆米', tier: '高客单',
      desc: '数码印花，取凤凰翼羽渐变，可作围巾亦可作装饰挂画。' },
    { id: 'box', image: 'assets/img/merch/r-box.webp', name: '东固文创礼盒', spec: '260 × 200 × 70 mm · 硬盒 + 磁扣', tier: '高客单',
      desc: '礼盒装徽章、书签、明信片与笔记本，外盒压印图腾。' },
    { id: 'wallpaper', image: 'assets/img/merch/r-wallpaper.webp', name: '数字壁纸 / 表情包', spec: '手机壁纸 1170 × 2532 · 表情 24 帧', tier: '数字衍生',
      desc: '凤凰飞舞动画导出的动态壁纸与「凤小畲」表情包，供二次传播。' }
  ],

  /* 场景路线：对应项目 AR 小程序规划的三大场景，三段均已在 AR 展陈馆内可看 */
  roadmap: [
    { id: 'carve', no: '01', scene: '造像 · 72 秒', title: '扫描传统造像', desc: '一木成像：选木 → 定像 → 开坯 → 修光 → 彩绘贴金 → 开光，一段樟木在同一条进度轴上被雕成神像', status: 'AR 展陈馆 · 场景一' },
    { id: 'red',   no: '02', scene: '红色 · 44 秒', title: '扫描红色地标', desc: '东固会师 / 龙冈大捷 / 白云山首战 / 六渡坳，四段历史场景复原 + 中英双语', status: 'AR 展陈馆 · 场景二' },
    { id: 'phoenix', no: '03', scene: '图腾 · 36 秒', title: '扫描畲族凤凰图腾', desc: '动态化凤凰飞舞动画与畲族文化介绍 · 文创延展', status: 'AR 展陈馆 · 场景三' }
  ]
};