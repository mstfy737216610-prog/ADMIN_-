import React, { useState } from 'react';
import { BotConfig, ForwardRule, SourceItem } from '../types/index.ts';
import {
  generateArabicTelethonScript,
  generateArabicBotScript,
  generateConfigFile,
  generateEnvFile,
  generateRequirementsTxt,
} from '../utils/codeGenerators.ts';
import {
  Code,
  Download,
  Copy,
  Check,
  Terminal,
  FileCode,
  Shield,
  HelpCircle,
  Server,
  Play,
  Brain,
  Layers,
  Database,
} from 'lucide-react';

interface Props {
  config: BotConfig;
  rules: ForwardRule[];
  sources: SourceItem[];
}

export const PythonScriptViewer: React.FC<Props> = ({ config, rules, sources }) => {
  const [activeTab, setActiveTab] = useState<'smart_edu' | 'sources' | 'state' | 'telethon' | 'env' | 'requirements'>('smart_edu');
  const [copied, setCopied] = useState(false);

  // Read smart_educational_forwarder.py from local workspace if possible or generated
  const smartEduScript = `#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
محرر المحتوى التعليمي الجامعي الذكي ومُعيد التوجيه التلقائي
Smart University Educational Content Editor & Multi-Source Auto-Forwarder
================================================================================
المطور الأصلي للأداة الأساسية: Redian Marku (https://github.com/redianmarku/Telegram-Autoforwarder)
الترخيص: رخصة معهد ماساتشوستس للتكنولوجيا (MIT License) - جميع الحقوق محفوظة للمطور الأصلي

التطوير والتعريب والذكاء الاصطناعي:
- توكن البوت: ${config.botToken}
- الآدمن المسؤول: ${config.adminUsername} (ID: ${config.adminId})
- مزود الذكاء الاصطناعي: ${config.ai.primaryModel} (عبر ${config.ai.apiBase})
- استبدال إعلانات المنافسين بإعلان خدماتك الطلابية
- مراقبة متعددة: قنوات تيليجرام، حسابات تويتر/X، وتغذيات RSS
================================================================================
"""

import os
import sys
import json
import time
import asyncio
import logging
import aiohttp
from datetime import datetime

BOT_TOKEN = "${config.botToken}"
ADMIN_ID = ${config.adminId || 0}
ADMIN_USERNAME = "${config.adminUsername}"

AI_BASE_URL = "${config.ai.apiBase}"
AI_API_KEY = "${config.ai.apiKey}"
PRIMARY_MODEL = "${config.ai.primaryModel}"
FALLBACK_MODEL = "${config.ai.fallbackModel}"

# يرجى تشغيل السكريبت عبر: python3 smart_educational_forwarder.py
# سيقوم بقراءة sources.json و state.json تلقائياً ومراقبة كل المصادر.
`;

  const sourcesJson = JSON.stringify(
    {
      _info: "Telegram University Educational AutoForwarder Watchlist",
      version: "2.0.0",
      lastUpdated: new Date().toISOString(),
      sources: sources,
    },
    null,
    2
  );

  const stateJson = JSON.stringify(
    {
      bot_status: "active",
      admin_id: config.adminId,
      admin_user: config.adminUsername,
      processed_count: 0,
      forwarded_count: 0,
      ad_replaced_count: 0,
      last_run_timestamp: new Date().toISOString(),
      last_processed_ids: sources.reduce((acc, s) => ({ ...acc, [s.target]: s.lastPostId || "0" }), {})
    },
    null,
    2
  );

  const envContent = `# Telegram University Educational AutoForwarder Pro
BOT_TOKEN="${config.botToken}"
ADMIN_ID="${config.adminId}"
ADMIN_USERNAME="${config.adminUsername}"

# AI Provider (DeepSeek-V4.1-Flash)
AI_BASE_URL="${config.ai.apiBase}"
AI_API_KEY="${config.ai.apiKey}"
PRIMARY_MODEL="${config.ai.primaryModel}"
FALLBACK_MODEL="${config.ai.fallbackModel}"

# Ad Replacement Settings
AD_REPLACEMENT_ENABLED="${config.adReplacement.enabled ? 'true' : 'false'}"
`;

  const requirementsContent = `# Python Dependencies for Educational AutoForwarder
aiohttp>=3.9.0
telethon>=1.36.0
python-dotenv>=1.0.0
feedparser>=6.0.10
requests>=2.31.0
`;

  const getActiveCode = () => {
    switch (activeTab) {
      case 'smart_edu':
        return {
          filename: 'smart_educational_forwarder.py',
          code: smartEduScript,
          lang: 'python',
        };
      case 'sources':
        return {
          filename: 'sources.json',
          code: sourcesJson,
          lang: 'json',
        };
      case 'state':
        return {
          filename: 'state.json',
          code: stateJson,
          lang: 'json',
        };
      case 'telethon':
        return {
          filename: 'TelegramForwarder_Arabic.py',
          code: generateArabicTelethonScript(config, rules),
          lang: 'python',
        };
      case 'env':
        return {
          filename: '.env',
          code: envContent,
          lang: 'shell',
        };
      case 'requirements':
        return {
          filename: 'requirements.txt',
          code: requirementsContent,
          lang: 'text',
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
            <span>حزمة الأكواد وملفات الإعدادات الجاهزة (Python Engine & Config)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            جميع الأكواد مهيأة بالتوكن والآدمن الجديد ({config.adminUsername}) ومزود الذكاء الاصطناعي مع حفظ حقوق المطور الأصلي (MIT)
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-sky-400" />}
            <span>{copied ? 'تم النسخ!' : 'نسخ الكود'}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>تنزيل {current.filename}</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <button
          onClick={() => setActiveTab('smart_edu')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'smart_edu'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Brain className="w-4 h-4 text-amber-400" />
          <span>محرر المحتوى الذكي (smart_educational_forwarder.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('sources')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'sources'
              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Layers className="w-4 h-4 text-sky-400" />
          <span>المصادر (sources.json)</span>
        </button>

        <button
          onClick={() => setActiveTab('state')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'state'
              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Database className="w-4 h-4 text-indigo-400" />
          <span>تتبع الحالة (state.json)</span>
        </button>

        <button
          onClick={() => setActiveTab('telethon')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'telethon'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <FileCode className="w-4 h-4 text-emerald-400" />
          <span>سكريبت تليثون (TelegramForwarder_Arabic.py)</span>
        </button>

        <button
          onClick={() => setActiveTab('env')}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold transition-all shrink-0 ${
            activeTab === 'env'
              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
              : 'bg-slate-950/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <span>البيئة (.env)</span>
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

        <pre className="p-4 text-slate-300 overflow-x-auto max-h-[380px] leading-relaxed text-left selection:bg-sky-500/30 selection:text-white" dir="ltr">
          <code>{current.code}</code>
        </pre>
      </div>

      {/* Commands Summary Banner */}
      <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-xs space-y-2.5">
        <div className="flex items-center gap-2 text-amber-400 font-bold">
          <Terminal className="w-4 h-4" />
          <span>أوامر الإدارة المتاحة للآدمن ({config.adminUsername}) عبر التيليجرام:</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[11px]" dir="ltr">
          <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-sky-300 font-bold">/status</span>
            <span className="text-slate-400 block text-[10px] mt-0.5">عرض الحالة والإحصائيات</span>
          </div>
          <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-emerald-300 font-bold">/sources</span>
            <span className="text-slate-400 block text-[10px] mt-0.5">عرض قائمة المصادر المراقبة</span>
          </div>
          <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-indigo-300 font-bold">/pause /resume</span>
            <span className="text-slate-400 block text-[10px] mt-0.5">إيقاف أو استئناف النشر</span>
          </div>
          <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
            <span className="text-amber-300 font-bold">/set_ad &lt;text&gt;</span>
            <span className="text-slate-400 block text-[10px] mt-0.5">تحديث إعلان الخدمات الطلابية</span>
          </div>
        </div>
      </div>
    </div>
  );
};
