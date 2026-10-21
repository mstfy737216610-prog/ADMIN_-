import React, { useState } from 'react';
import { BotConfig, BotInfo } from '../types/index.ts';
import {
  Smartphone,
  Shield,
  KeyRound,
  Brain,
  Repeat,
  CheckCircle2,
  AlertCircle,
  Play,
  Send,
  Lock,
  Database,
  ArrowRight,
  Layers,
  Copy,
  Check,
  Cpu,
  Terminal,
  Server,
  Zap,
} from 'lucide-react';

interface Props {
  config: BotConfig;
  onChange: (updated: BotConfig) => void;
  onTestBot?: (token: string) => void;
  isTestingBot?: boolean;
  botInfo?: BotInfo | null;
}

export const CredentialsPanel: React.FC<Props> = ({
  config,
  onChange,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'architecture' | 'session_login' | 'users_manager'>('architecture');
  const [copied, setCopied] = useState<string | null>(null);

  // Simulation state for Userbot Login flow (Phone -> OTP -> Session)
  const [simPhone, setSimPhone] = useState('+966501234567');
  const [simStep, setSimStep] = useState<'phone' | 'otp' | '2fa' | 'success'>('phone');
  const [simOtp, setSimOtp] = useState('');
  const [simPassword, setSimPassword] = useState('');
  const [generatedSession, setGeneratedSession] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);

  // Stored simulated sessions
  const [sessionsList, setSessionsList] = useState([
    {
      userId: 7607633343,
      username: '@M_S_F_G',
      phone: '+966501234567',
      sessionString: '1BVtsOHIBu3Q1x...[Telethon StringSession Encrypted]...9Wk2',
      status: 'active',
      campaignsCount: 2,
      lastActive: 'الآن (متصل 24/7)',
    },
    {
      userId: 5892147012,
      username: '@student_rep',
      phone: '+96590887766',
      sessionString: '1BVtsOHIBu9Z2p...[Telethon StringSession Encrypted]...7Lt1',
      status: 'active',
      campaignsCount: 1,
      lastActive: 'منذ 4 دقائق',
    },
  ]);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const startLoginSimulation = () => {
    if (!simPhone.trim()) return;
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
      setSimStep('otp');
    }, 1000);
  };

  const verifyOtpSimulation = () => {
    if (!simOtp.trim()) return;
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
      // Simulate 2FA check or success
      if (simOtp === '2fa') {
        setSimStep('2fa');
      } else {
        const dummySession = `1BVtsOHI${Math.random().toString(36).substring(2, 15)}K8aL0${Date.now()}Pq9_StringSession`;
        setGeneratedSession(dummySession);
        setSimStep('success');
        setSessionsList((prev) => [
          ...prev,
          {
            userId: Math.floor(1000000000 + Math.random() * 9000000000),
            username: '@new_registered_user',
            phone: simPhone,
            sessionString: dummySession,
            status: 'active',
            campaignsCount: 1,
            lastActive: 'الآن',
          },
        ]);
      }
    }, 1200);
  };

  const verify2FaSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setIsSimulating(false);
      const dummySession = `1BVtsOHI${Math.random().toString(36).substring(2, 15)}K8aL0${Date.now()}Pq9_StringSession_2FA`;
      setGeneratedSession(dummySession);
      setSimStep('success');
      setSessionsList((prev) => [
        ...prev,
        {
          userId: Math.floor(1000000000 + Math.random() * 9000000000),
          username: '@new_user_2fa',
          phone: simPhone,
          sessionString: dummySession,
          status: 'active',
          campaignsCount: 1,
          lastActive: 'الآن',
        },
      ]);
    }, 1200);
  };

  const resetSimulation = () => {
    setSimStep('phone');
    setSimOtp('');
    setSimPassword('');
    setGeneratedSession('');
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl relative overflow-hidden space-y-6">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">
              نظام اليوزربوت وجلسات المستخدمين (Userbot Multi-Session & AI Engine)
            </h2>
            <span className="px-2 py-0.5 text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-md font-mono">
              بدون توكن للبوت لقراءة القنوات
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            آلية عمل البوت تحت الغطاء: تسجيل دخول المستخدم واستخراج الجلسة (StringSession) والزحف المستقل دون استخدام جلسة الآدمن
          </p>
        </div>

        {/* Sub-tabs */}
        <div className="flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
          <button
            onClick={() => setActiveSubTab('architecture')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'architecture' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            <span>آلية العمل (تحت الغطاء)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('session_login')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'session_login' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>محاكاة تسجيل الجلسة (OTP)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('users_manager')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'users_manager' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>الجلسات المسجلة ({sessionsList.length})</span>
          </button>
        </div>
      </div>

      {/* TAB 1: UNDER THE HOOD ARCHITECTURE EXPLANATION */}
      {activeSubTab === 'architecture' && (
        <div className="space-y-5">
          {/* Top Banner Notice */}
          <div className="p-4 bg-indigo-950/40 border border-indigo-800/40 rounded-xl flex items-start gap-3">
            <Shield className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <h3 className="font-bold text-white text-sm">
                لماذا لا نستخدم توكن البوت العادي (Bot API) لقراءة القنوات؟
              </h3>
              <p className="text-slate-300 leading-relaxed">
                البوتات الرسمية التي تعتمد على توكن <code className="text-amber-300 font-mono">@BotFather</code> لا تملك أي صلاحية تقنية لقراءة منشورات القنوات العامة أو الخاصة إلا إذا تم تعيينها كمشرف (Admin) داخل كل قناة. ولأننا نراقب قنوات جامعية ورسمية لا نملك إدارتها، قمنا ببناء <strong>يوزربوت (Userbot)</strong> عبر مكتبة Telethon يتصرف كحساب مستخدم حقيقي تماماً.
              </p>
            </div>
          </div>

          {/* 4 Pillars of the Workflow */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 1. How Channels Are Read */}
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="w-6 h-6 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold text-xs">
                  1
                </span>
                <span className="text-[10px] font-mono text-slate-500">Telethon StringSession</span>
              </div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Smartphone className="w-4 h-4 text-sky-400" />
                <span>كيف يقرأ البوت القنوات؟ (حل مشكلة الـ API)</span>
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                عندما يرسل المستخدم رقمه وكود التحقق (OTP)، يستخرج الكود <strong>الجلسة النصية (Session String)</strong>، وهي بمثابة المفتاح السري للحساب. يفتح عامل الزحف (<code className="text-sky-300 font-mono">worker.py</code>) اتصالاً بصفته هذا المستخدم، فيرى ما يراه المستخدم ويقرأ المنشورات فور نزولها دون الحاجة لرتبة إشراف.
              </p>
            </div>

            {/* 2. AI Processing & SKIP logic */}
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="w-6 h-6 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-xs">
                  2
                </span>
                <span className="text-[10px] font-mono text-slate-500">DeepSeek & SKIP Logic</span>
              </div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Brain className="w-4 h-4 text-purple-400" />
                <span>المعالجة بالذكاء الاصطناعي (AI Processing)</span>
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                عند التقاط رسالة جديدة، يتوقف النشر مؤقتاً، ويُرسل النص لنموذج <code className="text-purple-300 font-mono">DeepSeek</code> عبر طلب POST مشفر مع تعليمات الصياغة. إذا رد النموذج بـ <strong className="text-rose-400 font-mono">SKIP</strong> (منشور غير ملائم أو تافه)، تُمسح الرسالة فوراً. إذا رد بنص معاد صياغته كمنشور أصلي وحصري، يُمرر للنشر.
              </p>
            </div>

            {/* 3. Publishing with User Session */}
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                  3
                </span>
                <span className="text-[10px] font-mono text-slate-500">Direct User Publishing</span>
              </div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Send className="w-4 h-4 text-emerald-400" />
                <span>كيف ينشر البوت في قناة الهدف؟</span>
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                يستخدم البوت نفس جلسة المستخدم (<code className="text-emerald-300 font-mono">Session String</code>) لتنفيذ أمر <code className="text-emerald-300 font-mono">send_message</code> أو <code className="text-emerald-300 font-mono">send_file</code> في قناة الهدف التي حددها في حملته، فتظهر الرسالة في القناة كأن المستخدم نفسه هو من كتبها ونشرها، مع الحفاظ على جودة الصور والملفات.
              </p>
            </div>

            {/* 4. Anti-Duplication & While Loop */}
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-xs">
                  4
                </span>
                <span className="text-[10px] font-mono text-slate-500">ID &gt; last_processed_id</span>
              </div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Repeat className="w-4 h-4 text-amber-400" />
                <span>منع التكرار وحلقة الـ While Loop</span>
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                يعمل عامل الزحف في حلقة لا نهائية (While Loop). ولكي لا ينشر نفس الخبر مرتين، يتم حفظ <strong className="text-amber-300 font-mono">last_processed_id</strong> لكل قناة في قاعدة بيانات SQLite. في كل دورة، يقرأ فقط الرسائل التي تحمل <code className="text-amber-300 font-mono">ID &gt; last_processed_id</code> مع فحص بصمة الهاش.
              </p>
            </div>
          </div>

          {/* Strict Security Isolation Banner */}
          <div className="p-4 bg-rose-950/30 border border-rose-800/40 rounded-xl flex items-start gap-3">
            <Lock className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <h3 className="font-bold text-white text-sm">
                قاعدة العزل الأمني الصارمة (Strict Security Rule)
              </h3>
              <p className="text-rose-200 leading-relaxed">
                ملف <code className="text-white font-mono bg-rose-950 px-1.5 py-0.5 rounded">worker.py</code> مصمم برمجياً بحيث <strong>لا يستخدم جلسة الأدمن إطلاقاً للقيام بعمليات المستخدمين</strong>. كل مستخدم يملك خيط اتصال منفصل بجلسته الخاصة المستقلة، وتتم عملية الزحف والنشر باسمه فقط.
              </p>
            </div>
          </div>

          {/* 3 Core Architecture Files */}
          <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-xs space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <Cpu className="w-4 h-4 text-sky-400" />
              <span>الملفات الثلاثة الأساسية المعتمدة في النظام:</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-amber-400 font-bold font-mono block text-xs">1. main.py</span>
                <span className="text-slate-400 block text-[11px] mt-1">
                  البوت الأساسي عبر Telethon: يستقبل أوامر المستخدمين (/start)، ويدير التسجيل (رقم الهاتف، OTP، 2FA، واستخراج الجلسة)، وخادم Keep-Alive.
                </span>
              </div>

              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-sky-400 font-bold font-mono block text-xs">2. worker.py</span>
                <span className="text-slate-400 block text-[11px] mt-1">
                  عامل الزحف بالخلفية: يقرأ المصادر من قاعدة البيانات، ويفتح اتصالاً بكل مستخدم بجلسته الخاصة، يمرر للذكاء الاصطناعي، وينشر في القناة الهدف.
                </span>
              </div>

              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <span className="text-indigo-400 font-bold font-mono block text-xs">3. database.py</span>
                <span className="text-slate-400 block text-[11px] mt-1">
                  طبقة SQLite: إدارة المستخدمين، الجلسات المشفرة، الحملات، المصادر، منع التكرار، والسجلات.
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: INTERACTIVE LOGIN SIMULATOR (PHONE -> OTP -> 2FA -> SESSION) */}
      {activeSubTab === 'session_login' && (
        <div className="space-y-4">
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-sky-400" />
                <span>محاكاة تجربة تسجيل الدخول الحية (OTP Login Flow Simulator)</span>
              </h3>
              <button
                onClick={resetSimulation}
                className="text-xs text-slate-400 hover:text-white underline cursor-pointer"
              >
                إعادة المحاكاة
              </button>
            </div>

            <p className="text-xs text-slate-400">
              هذه المحاكاة توضح تماماً ما يحدث عندما يتفاعل المستخدم الحقيقي مع البوت في تيليجرام لاستخراج الجلسة النصية (StringSession).
            </p>

            {/* Stepper Progress */}
            <div className="flex items-center justify-between max-w-md mx-auto py-2">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                    simStep === 'phone'
                      ? 'bg-sky-500 text-white'
                      : 'bg-emerald-500 text-white'
                  }`}
                >
                  {simStep === 'phone' ? '1' : '✓'}
                </div>
                <span className="text-[10px] text-slate-400">إدخال الرقم</span>
              </div>

              <div className="w-12 h-0.5 bg-slate-800"></div>

              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                    simStep === 'otp'
                      ? 'bg-sky-500 text-white'
                      : simStep === '2fa' || simStep === 'success'
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {simStep === '2fa' || simStep === 'success' ? '✓' : '2'}
                </div>
                <span className="text-[10px] text-slate-400">رمز الـ OTP</span>
              </div>

              <div className="w-12 h-0.5 bg-slate-800"></div>

              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                    simStep === 'success'
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {simStep === 'success' ? '✓' : '3'}
                </div>
                <span className="text-[10px] text-slate-400">استخراج الجلسة</span>
              </div>
            </div>

            {/* Step 1: Phone */}
            {simStep === 'phone' && (
              <div className="max-w-md mx-auto p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <label className="block text-xs font-semibold text-slate-300">
                  رقم هاتف المستخدم (مع الرمز الدولي):
                </label>
                <input
                  type="text"
                  value={simPhone}
                  onChange={(e) => setSimPhone(e.target.value)}
                  placeholder="+966501234567"
                  dir="ltr"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white font-mono"
                />
                <button
                  onClick={startLoginSimulation}
                  disabled={isSimulating}
                  className="w-full py-2.5 bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSimulating ? (
                    <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  <span>إرسال كود التحقق (send_code_request)</span>
                </button>
              </div>
            )}

            {/* Step 2: OTP */}
            {simStep === 'otp' && (
              <div className="max-w-md mx-auto p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <div className="text-xs text-amber-300 bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/30">
                  📩 وصلك رمز تحقق من تيليجرام للرقم <code className="text-white font-mono">{simPhone}</code>.
                  (جرب إدخال أي 5 أرقام مثل <code className="text-white font-mono">12345</code> أو اكتب <code className="text-white font-mono">2fa</code> لاختبار التحقق بخطوتين).
                </div>
                <label className="block text-xs font-semibold text-slate-300">
                  رمز التحقق (Telegram OTP Code):
                </label>
                <input
                  type="text"
                  value={simOtp}
                  onChange={(e) => setSimOtp(e.target.value)}
                  placeholder="12345"
                  dir="ltr"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white font-mono text-center tracking-widest text-lg"
                />
                <button
                  onClick={verifyOtpSimulation}
                  disabled={isSimulating}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSimulating ? (
                    <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  <span>توثيق الرمز واستخراج الجلسة (sign_in)</span>
                </button>
              </div>
            )}

            {/* Step 2.5: 2FA Password */}
            {simStep === '2fa' && (
              <div className="max-w-md mx-auto p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <div className="text-xs text-indigo-300 bg-indigo-500/10 p-2.5 rounded-lg border border-indigo-500/30">
                  🔐 حسابك محمي بالتحقق بخطوتين (SessionPasswordNeededError). يرجى إدخال كلمة المرور السحابية.
                </div>
                <label className="block text-xs font-semibold text-slate-300">
                  كلمة المرور السحابية (Two-Step Verification Password):
                </label>
                <input
                  type="password"
                  value={simPassword}
                  onChange={(e) => setSimPassword(e.target.value)}
                  placeholder="••••••••"
                  dir="ltr"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white font-mono"
                />
                <button
                  onClick={verify2FaSimulation}
                  disabled={isSimulating}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSimulating ? (
                    <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
                  ) : (
                    <Lock className="w-4 h-4" />
                  )}
                  <span>تأكيد كلمة المرور وحفظ الجلسة</span>
                </button>
              </div>
            )}

            {/* Step 3: Success Result */}
            {simStep === 'success' && (
              <div className="max-w-lg mx-auto p-4 bg-emerald-950/30 border border-emerald-500/30 rounded-xl space-y-3 text-xs">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>تم استخراج الجلسة النصية (StringSession) وتخزينها بنجاح!</span>
                </div>
                <p className="text-slate-300">
                  تم حفظ الجلسة داخل قاعدة بيانات SQLite (<code className="text-white font-mono">database.py</code>) الخاصة برقم المستخدم <code className="text-white font-mono">{simPhone}</code>.
                </p>

                <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 font-mono text-[11px] text-emerald-300 break-all select-all flex items-center justify-between">
                  <span>{generatedSession}</span>
                  <button
                    onClick={() => handleCopy(generatedSession, 'sim_session')}
                    className="p-1 text-slate-400 hover:text-white shrink-0 ml-2"
                  >
                    {copied === 'sim_session' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>

                <div className="pt-2 text-[11px] text-slate-400">
                  🚀 عامل الزحف (<code className="text-sky-300 font-mono">worker.py</code>) أصبح قادراً الآن على الزحف للقنوات باسم هذا الحساب ونشر المنشورات في قناته مباشرة!
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: REGISTERED SESSIONS IN SQLITE DATABASE */}
      {activeSubTab === 'users_manager' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-400" />
              <span>قائمة حسابات المستخدمين والجلسات النشطة في قاعدة البيانات (SQLite Users &amp; Sessions):</span>
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">
              جداول: users, campaigns, sources
            </span>
          </div>

          <div className="space-y-2.5">
            {sessionsList.map((user, idx) => (
              <div
                key={idx}
                className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 flex items-center justify-center font-bold font-mono text-xs">
                    {idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{user.username}</span>
                      <span className="text-slate-400 font-mono text-[11px]">({user.phone})</span>
                      <span className="px-2 py-0.5 bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 rounded-md text-[10px]">
                        {user.status === 'active' ? 'جلسة نشطة 🟢' : 'متوقف'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                      معرف المستخدم: {user.userId} | الحملات: {user.campaignsCount} | آخر نشاط: {user.lastActive}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end md:self-center">
                  <div className="px-2 py-1 bg-slate-900 border border-slate-800 rounded text-[11px] font-mono text-slate-400 max-w-[180px] truncate" dir="ltr">
                    {user.sessionString}
                  </div>
                  <button
                    onClick={() => handleCopy(user.sessionString, `user_${idx}`)}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700"
                    title="نسخ الجلسة"
                  >
                    {copied === `user_${idx}` ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
