/* ============================================================
 * auth.js — 27秋招多用户认证库（纯前端 localStorage 方案）
 * 用法：在所有页面 <script src="auth.js"> 之后调用：
 *   const u = currentUser();          // {uid, username} | null
 *   if(!u) location.href='login.html';
 *   trackKey('qiuzhao27_track_v1')    // -> qiuzhao27_track_<uid>（按用户隔离）
 * ============================================================ */
(function(){
  const USERS_KEY = 'qiuzhao27_users_v1';
  const SESSION_KEY = 'qiuzhao27_session_v1';
  // 旧版（无用户后缀）的数据 key —— 用于首次登录时迁移老数据
  const LEGACY_KEYS = ['qiuzhao27_track_v1', 'qiuzhao27_entries_v1', 'qiuzhao27_mail_processed_v1'];

  /* ---------- 基础工具 ---------- */
  function getJSON(key, def){
    try{ const v = localStorage.getItem(key); return v ? JSON.parse(v) : def; }catch(e){ return def; }
  }
  function setJSON(key, val){
    try{ localStorage.setItem(key, JSON.stringify(val)); }catch(e){}
  }

  /* ---------- 密码哈希（本地应用防明文，非安全级） ---------- */
  function hashPwd(username, pwd){
    let h = 5381;
    const s = username + '::' + pwd + '::qiuzhao27salt';
    for(let i=0;i<s.length;i++){ h = ((h<<5)+h+s.charCodeAt(i))|0; }
    return 'h' + (h>>>0).toString(36) + '_' + s.length;
  }

  /* ---------- 用户管理 ---------- */
  function getUsers(){ return getJSON(USERS_KEY, []); }
  function saveUsers(users){ setJSON(USERS_KEY, users); }

  function register(username, password){
    username = (username||'').trim();
    if(username.length < 2) return {ok:false, msg:'用户名至少 2 个字符'};
    if(!/^[\w\u4e00-\u9fa5]{2,20}$/.test(username)) return {ok:false, msg:'用户名仅限中文/字母/数字/下划线，2-20位'};
    if((password||'').length < 4) return {ok:false, msg:'密码至少 4 位'};
    const users = getUsers();
    if(users.some(u=>u.username===username)) return {ok:false, msg:'该用户名已被注册'};
    const uid = 'u' + Date.now().toString(36) + Math.random().toString(36).slice(2,7);
    const user = {uid, username, passHash: hashPwd(username, password), createdAt: new Date().toLocaleString('zh-CN',{hour12:false})};
    users.push(user);
    saveUsers(users);
    // 仅当这是「第一个用户」时才迁移旧版无用户数据（避免后续账号继承他人数据）
    if(users.length === 1){
      migrateLegacy(uid);
    }
    setSession(user);
    return {ok:true, user};
  }

  function login(username, password){
    username = (username||'').trim();
    const users = getUsers();
    const u = users.find(x=>x.username===username);
    if(!u) return {ok:false, msg:'用户名不存在'};
    if(u.passHash !== hashPwd(username, password)) return {ok:false, msg:'密码错误'};
    setSession(u);
    return {ok:true, user:u};
  }

  function logout(){
    try{ localStorage.removeItem(SESSION_KEY); }catch(e){}
  }

  /* ---------- 会话 ---------- */
  function setSession(user){ setJSON(SESSION_KEY, {uid:user.uid, username:user.username, loginAt:Date.now()}); }
  function currentUser(){
    const s = getJSON(SESSION_KEY, null);
    if(!s || !s.uid) return null;
    // 校验用户仍存在
    const users = getUsers();
    const u = users.find(x=>x.uid===s.uid);
    if(!u) return null;
    return {uid:u.uid, username:u.username};
  }

  /* ---------- 数据 key 隔离 ---------- */
  function userKey(base){
    const u = currentUser();
    return u ? (base + '_' + u.uid) : base;
  }

  /* ---------- 旧数据迁移（仅第一个用户注册时调用） ---------- */
  function migrateLegacy(uid){
    try{
      LEGACY_KEYS.forEach(base=>{
        const legacy = localStorage.getItem(base);
        if(legacy === null) return;
        const newKey = base + '_' + uid;
        if(localStorage.getItem(newKey) === null){
          localStorage.setItem(newKey, legacy);
        }
        // 迁移后删除旧 key：确保后续注册的账号不会再次继承旧数据（数据隔离关键）
        try{ localStorage.removeItem(base); }catch(e){}
      });
    }catch(e){}
  }

  /* ---------- 导出全局 API ---------- */
  window.Auth = {
    register, login, logout, currentUser, userKey,
    hashPwd, getUsers,
  };
})();
