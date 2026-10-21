import React, { useState, useEffect } from 'react';
import { BotConfig, ForwardRule, SourceItem } from '../types/index.ts';
import {
  Code,
  Download,
  Copy,
  Check,
  Terminal,
  FileCode,
  Shield,
  Server,
  Play,
  Brain,
  Layers,
  Database,
  Smartphone,
  Cloud,
  RefreshCw,
} from 'lucide-react';

interface Props {
  config: BotConfig;
  rules: ForwardRule[];
  sources: SourceItem[];
}

export const PythonScriptViewer: React.FC<Props> = ({ config, rules, sources }) => {
  const [activeTab, setActiveTab] = useState<'main' | 'worker' | 'database' | 'campaigns' | 'requirements' | 'procfile' | 'env'>('main');
  const [copied, setCopied] = useState(false);
  const [fileContents, setFileContents] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch real file content from server
  useEffect(() => {
    const fetchFile = async (filename: string) => {
      try {
        setLoading(true);
        const res = await fetch(`/api/file-content?file=${filename}`);
        if (res.ok) {
          const data = await res.json();
          setFileContents((prev) => ({ ...prev, [filename]: data.content }));
        }
      } catch (e) {
        console.warn(`Failed to fetch ${filename}`, e);
      } finally {
        setLoading(false);
      }
    };

    const targetFile =
      activeTab === 'main'
        ? 'main.py'
        : activeTab === 'worker'
        ? 'worker.py'
        : activeTab === 'database'
        ? 'database.py'
        : activeTab === 'campaigns'
        ? 'campaigns.json'
        : activeTab === 'requirements'
        ? 'requirements.txt'
        : activeTab === 'procfile'
        ? 'Procfile'
        : '.env.example';

    if (!fileContents[targetFile]) {
      fetchFile(targetFile);
    }
  }, [activeTab, fileContents]);

  const getActiveCode = () => {
    switch (activeTab) {
      case 'main':
        return {
          filename: 'main.py',
          code: fileContents['main.py'] || '# جاري جلب محتوى main.py...',
          lang: 'python',
          desc: 'البوت الأساسي لإدارة المستخدمين وتسجيل الدخول واستخراج الجلسات (StringSession) والرد التفاعلي',
        };
      case 'worker':
        return {
          filename: 'worker.py',
          code: fileContents['worker.py'] || '# جاري جلب محتوى worker.py...',
          lang: 'python',
          desc: 'عامل الزحف والنشر في الخلفية (Background Crawler): يفتح اتصالاً مستقلاً بجلسة كل مستخدم ويمرر المنشورات للذكاء الاصطناعي',
        };
      case 'database':
        return {
          filename: 'database.py',
          code: fileContents['database.py'] || '# جاري جلب محتوى database.py...',
          lang: 'python',
          desc: 'طبقة قاعدة بيانات SQLite لإدارة الحسابات، الجلسات، الحملات، القنوات، ومنع التكرار (Anti-Duplication)',
        };
      case 'campaigns':
        return {
          filename: 'campaigns.json',
          code: fileContents['campaigns.json'] || JSON.stringify({ campaigns: [] }, null, 2),
          lang: 'json',
          desc: 'ملف إعدادات الحملات وقنوات النشر والمصادر وقواعد الفلترة واستبدال الإعلانات',
        };
      case 'requirements':
        return {
          filename: 'requirements.txt',
          code: fileContents['requirements.txt'] || 'telethon>=1.36.0\naiohttp>=3.9.0\npython-dotenv>=1.0.0\nrequests>=2.31.0',
          lang: 'text',
          desc: 'مكتبات بايثون المطلوبة للاستضافات المجانية والـ VPS (Telethon, Aiohttp, etc.)',
        };
      case 'procfile':
        return {
          filename: 'Procfile',
          code: fileContents['Procfile'] || 'web: python3 main.py\nworker: python3 worker.py',
          lang: 'text',
          desc: 'أمر تشغيل البوت وعامل الزحف على منصات Heroku و Render و Railway',
        };
      case 'env':
        return {
          filename: '.env',
          code: fileContents['.env.example'] || `BOT_TOKEN="${config.botToken}"\nADMIN_ID="${config.adminId}"\nADMIN_USERNAME="${config.adminUsername}"\nAI_BASE_URL="${config.ai.apiBase}"\nAI_API_KEY="${config.ai.apiKey}"\nPRIMARY_MODEL="${config.ai.primaryModel}"`,
          lang: 'shell',
          desc: 'متغيرات البيئة للتوكن والآدمن ومزود الذكاء الاصطناعي (DeepSeek)',
        };
    }
  };

  const current = getActiveCode();

  const handleCopy = () => {
    navigator.clipboard.writeText(current.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([current.code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = current.filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Code className="w-5 h-5 text-emerald-400" />
            <span>حزمة الأكواد الرسمية ومحرك الزحف متعدد الجلسات (Python Multi-User Engine)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            الهيكل المعتمد بدقة: <code className="text-amber-300 font-mono">main.py</code> (البوت والجلسات) + <code className="text-sky-300 font-mono">worker.py</code> (الزحف والنشر) + <code className="text-indigo-300 font-mono">database.py</code> (قاعدة البيانات)
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-sky-400" />}
            <span>{copied ? 'تم النسخ!' : 'نسخ الكود'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            <Download className="w-4 h-4 text-emerald-400" />
            <span>تنزيل {current.filename}</span>
          </button>

          <a
            href="/Telegram_Educational_Bot_GitHub_Package.zip"
            download="Telegram_Educational_Bot_GitHub_Package.zip"
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-purple-600/20 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>تحميل كامل حزمة GitHub (ZIP)</span>
          </a>
        </div>
      </div>

      {/* Architecture Highlights Banner */}
      <div className="p-3.5 bg-slate-950/80 rounded-xl border border-slate-800 text-xs text-slate-300 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sky-400 font-semibold">
          <Shield className="w-4 h-4 text-sky-400 shrink-0" />
          <span>مبدأ العزل الأمني: كل مستخدم يزحف وينشر بجلسة حسابه الخاصة (Telethon StringSession)، وجلسة المشرف لا تستخدم لعمليات الآخرين.</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-emerald-400 font-mono shrink-0">
          <Server className="w-3.5 h-3.5" />
          <span>Keep-Alive Server مدمج على المنفذ 8088 للاستضافات المجانية</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <button
          onClick={() => setActiveTab('main')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'main'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Smartphone className="w-4 h-4 text-amber-400" />
          <span>البوت وإدارة الجلسات (main.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('worker')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'worker'
              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Play className="w-4 h-4 text-sky-400" />
          <span>عامل الزحف والنشر (worker.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('database')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'database'
              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Database className="w-4 h-4 text-indigo-400" />
          <span>قاعدة بيانات SQLite (database.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('campaigns')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'campaigns'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Layers className="w-4 h-4 text-emerald-400" />
          <span>الحملات (campaigns.json)</span>
        </button>

        <button
          onClick={() => setActiveTab('requirements')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'requirements'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <span>المكتبات (requirements.txt)</span>
        </button>

        <button
          onClick={() => setActiveTab('procfile')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'procfile'
              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <span>أمر الاستضافة (Procfile)</span>
        </button>

        <button
          onClick={() => setActiveTab('env')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'env'
              ? 'bg-pink-500/20 text-pink-300 border border-pink-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <span>البيئة (.env)</span>
        </button>
      </div>

      {/* Description banner */}
      <div className="px-3.5 py-2 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-400 flex items-center justify-between">
        <span>{current.desc}</span>
        {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400" />}
      </div>

      {/* Code Viewer */}
      <div className="relative rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden font-mono text-xs">
        <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-800 text-slate-400">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-rose-500/70"></div>
            <div className="w-3 h-3 rounded-full bg-amber-500/70"></div>
            <div className="w-3 h-3 rounded-full bg-emerald-500/70"></div>
            <span className="text-slate-300 font-semibold ml-2 text-xs">{current.filename}</span>
          </div>
          <span className="text-[10px] text-slate-500">
            {current.code.split('\n').length} أسطر
          </span>
        </div>

        <pre className="p-4 text-slate-300 overflow-x-auto max-h-[420px] leading-relaxed text-left selection:bg-sky-500/30 selection:text-white" dir="ltr">
          <code>{current.code}</code>
        </pre>
      </div>

      {/* Instructions on Running for Free Hosts */}
      <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-xs space-y-2.5">
        <div className="flex items-center gap-2 text-amber-400 font-bold">
          <Terminal className="w-4 h-4" />
          <span>طرق التشغيل المعتمدة في مختلف بيئات الاستضافة:</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 font-mono text-[11px]" dir="ltr">
          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-sky-300 font-bold block mb-1">1. خادم مجاني فردي (All-in-One):</span>
            <code className="text-emerald-300 bg-slate-950 px-1 py-0.5 rounded block">python3 main.py</code>
            <span className="text-slate-400 text-[10px] mt-1 block">يشغل البوت وعامل الزحف وخادم الـ Keep-Alive تلقائياً معاً</span>
          </div>

          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-purple-300 font-bold block mb-1">2. نمط الخدمات المنفصلة (Worker):</span>
            <code className="text-emerald-300 bg-slate-950 px-1 py-0.5 rounded block">python3 worker.py</code>
            <span className="text-slate-400 text-[10px] mt-1 block">تشغيل عامل الزحف كخدمة خلفية مستقلة 24/7</span>
          </div>

          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-indigo-300 font-bold block mb-1">3. تطبيق بوت بزنس (Bots.Business):</span>
            <code className="text-emerald-300 bg-slate-950 px-1 py-0.5 rounded block">Import from Git</code>
            <span className="text-slate-400 text-[10px] mt-1 block">الملفات جاهزة مع bot.json ومجلد commands</span>
          </div>
        </div>
      </div>
    </div>
  );
};
