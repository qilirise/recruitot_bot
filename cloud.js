/* ============================================================
 * cloud.js - 云端存储层（GitHub Gist 同步）
 * ------------------------------------------------------------
 * 目标：同一账号跨设备共享数据（投递/测评/面试/Offer/邮件处理/隐藏offer）
 * 原理：
 *   - 每个账号的数据打包为 JSON，存入一个「私有 Gist」
 *   - 用户提供自己的 GitHub PAT（仅需 gist 权限），存于浏览器 localStorage（按账号隔离）
 *   - 数据变更 -> 防抖推送 Gist；页面加载 -> 拉取 Gist 合并
 *   - 未绑定 PAT 时完全回退 localStorage（现有功能不受影响）
 * 注意：PAT 只存浏览器本地，绝不写入代码/仓库/服务器
 * ============================================================ */
(function(){
  const CFG_PREFIX = 'qiuzhao27_cloud_';   // qiuzhao27_cloud_<uid> = {token, gistId, lastSync}
  const DATA_KEY = 'data.json';
  let _timer = null;

  /* ---------- 配置存取 ---------- */
  function cfgKey(){ return CFG_PREFIX + (window.CURRENT_USER ? CURRENT_USER.uid : 'anon'); }
  function getCfg(){ try{ return JSON.parse(localStorage.getItem(cfgKey())) || null; }catch(e){ return null; } }
  function setCfg(c){ try{ localStorage.setItem(cfgKey(), JSON.stringify(c)); }catch(e){} }

  /* ---------- 打包 / 解包账号数据 ---------- */
  // 收集当前账号在 localStorage 中的全部数据 key（按 uid 隔离）
  function collectData(){
    const uid = window.CURRENT_USER ? CURRENT_USER.uid : 'anon';
    const keys = ['qiuzhao27_track_v1','qiuzhao27_entries_v1','qiuzhao27_mail_processed_v1','qiuzhao27_hided_v1'];
    const out = {};
    keys.forEach(base=>{
      const k = base + '_' + uid;
      const v = localStorage.getItem(k);
      if(v !== null) out[base] = v;
    });
    out['_uid'] = uid;
    out['_ts'] = Date.now();
    return out;
  }
  // 把云端数据写回 localStorage（仅写入已存在的 key；保留本地已有数据用 merge=true）
  function applyData(data, merge){
    if(!data || typeof data !== 'object') return;
    const uid = window.CURRENT_USER ? CURRENT_USER.uid : 'anon';
    const keys = ['qiuzhao27_track_v1','qiuzhao27_entries_v1','qiuzhao27_mail_processed_v1','qiuzhao27_hided_v1'];
    keys.forEach(base=>{
      const k = base + '_' + uid;
      if(data[base] === undefined) return;
      if(merge){
        const local = localStorage.getItem(k);
        if(local === null || local === undefined){ localStorage.setItem(k, data[base]); }
        // 本地已有则保留本地（个人工具：以本机最近操作优先）
      } else {
        localStorage.setItem(k, data[base]);
      }
    });
  }

  /* ---------- Gist API ---------- */
  function api(url, opts, token){
    return fetch(url, Object.assign({
      headers: {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'qiuzhao27-cloud'
      }
    }, opts||{})).then(r=>{
      if(r.status === 401) throw new Error('Token 无效或已过期');
      if(r.status === 403) throw new Error('Token 权限不足（需要 gist 权限）');
      if(r.status === 404) throw new Error('Gist 不存在');
      if(!r.ok) throw new Error('GitHub API ' + r.status);
      return r.status === 204 ? null : r.json();
    });
  }

  /* ---------- 绑定：验证 token 并创建/复用私有 gist ---------- */
  async function bind(token){
    token = (token||'').trim();
    if(!token) return {ok:false, msg:'请填写 GitHub PAT'};
    const uid = window.CURRENT_USER ? CURRENT_USER.uid : 'anon';
    try{
      // 1) 验证 token
      const user = await api('https://api.github.com/user', {method:'GET'}, token);
      // 2) 查询该账号已绑定的 gist（按描述前缀查找）
      const gists = await api('https://api.github.com/gists?per_page=100', {method:'GET'}, token);
      let gist = (gists||[]).find(g=>g.description === ('qiuzhao27-' + uid));
      // 3) 不存在则创建私有 gist
      if(!gist){
        gist = await api('https://api.github.com/gists', {
          method:'POST',
          body: JSON.stringify({
            description: 'qiuzhao27-' + uid,
            public: false,
            files: { [DATA_KEY]: { content: JSON.stringify(collectData()) } }
          })
        }, token);
      }
      setCfg({token: token, gistId: gist.id, boundUser: user.login, lastSync: Date.now()});
      return {ok:true, gistId: gist.id, user: user.login};
    }catch(e){
      return {ok:false, msg: e.message};
    }
  }

  /* ---------- 推送：本地数据 -> Gist（防抖） ---------- */
  function schedulePush(){
    if(_timer) clearTimeout(_timer);
    _timer = setTimeout(()=>{ push(); }, 2500);
  }
  async function push(){
    const cfg = getCfg();
    if(!cfg || !cfg.token || !cfg.gistId) return false;
    const uid = window.CURRENT_USER ? CURRENT_USER.uid : 'anon';
    const data = collectData();
    try{
      await api('https://api.github.com/gists/' + cfg.gistId, {
        method:'PATCH',
        body: JSON.stringify({ files: { [DATA_KEY]: { content: JSON.stringify(data) } } })
      }, cfg.token);
      cfg.lastSync = Date.now();
      setCfg(cfg);
      return true;
    }catch(e){ return false; }
  }

  /* ---------- 拉取：Gist -> 本地（登录后调用，合并策略） ---------- */
  async function pull(merge){
    const cfg = getCfg();
    if(!cfg || !cfg.token || !cfg.gistId) return {ok:false, msg:'未绑定云同步'};
    try{
      const gist = await api('https://api.github.com/gists/' + cfg.gistId, {method:'GET'}, cfg.token);
      const content = gist.files && gist.files[DATA_KEY] ? gist.files[DATA_KEY].content : null;
      if(content){
        const data = JSON.parse(content);
        applyData(data, merge !== false);
      }
      cfg.lastSync = Date.now();
      setCfg(cfg);
      return {ok:true, syncAt: new Date(cfg.lastSync).toLocaleString('zh-CN',{hour12:false})};
    }catch(e){
      return {ok:false, msg: e.message};
    }
  }

  /* ---------- 解除绑定 ---------- */
  function unbind(){
    try{ localStorage.removeItem(cfgKey()); }catch(e){}
  }

  /* ---------- 状态 ---------- */
  function status(){
    const cfg = getCfg();
    if(!cfg) return {bound:false};
    return {bound:true, user: cfg.boundUser, syncAt: cfg.lastSync ? new Date(cfg.lastSync).toLocaleString('zh-CN',{hour12:false}) : '--'};
  }

  window.Cloud = { bind, unbind, push, pull, schedulePush, status };
})();
