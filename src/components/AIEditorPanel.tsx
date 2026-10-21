import React, { useState } from 'react';
import { AIModelConfig } from '../types/index.ts';
import {
  Brain,
  Sparkles,
  Search,
  Key,
  Globe,
  Sliders,
  CheckCircle2,
  FileCode,
  HelpCircle,
  MessageSquare,
  Wand2,
} from 'lucide-react';

interface Props {
  aiConfig: AIModelConfig;
  onChange: (updated: AIModelConfig) => void;
}

export const AIEditorPanel: React.FC<Props> = ({ aiConfig, onChange }) => {
  const [showKey, setShowKey] = useState(false);
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);

  const presetInstructions = [
    {
      label: '👑 مشرف قروبات جامعية نشط',
      text: 'كن مثل مشرفين القروبات الجامعية المخلصين الذي يبحث عن الأخبار الجديدة ويعطيها للطلاب بأسلوب ودود ومباشر.',
    },
    {
      label: '📅 التركيز على المواعيد والنتائج',
      text: 'ركز بشكل أساسي على إبراز تواريخ بدء وانتهاء التسجيل، ونسب القبول، وشروط التقديم بخط بارز.',
    },
    {
      label: '📚 ناشر كتب ومراجع PDF',
      text: 'إذا كان المنشور يحتوي على كتاب أو ملخص أو ملف PDF، صف محتواه وفائدته الأكاديمية وشجع الطلاب على تحميله.',
    },
    {
      label: '🎯 أسلوب إخباري أكاديمي رسمي',
      text: 'اجعل اللغة رصينة وأكاديمية ومقتضبة، خالية من الحشو، مع التركيز على القرارات الرسمية فقط.',
    },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            <span>محرك الذكاء الاصطناعي: محرر المحتوى التعليمي (DeepSeek-V4.1-Flash)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            إعادة صياغة الأخبار والمنشورات الجامعية بأسلوب أكاديمي دقيق ومنظم مع ميزة البحث والتحقق
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>DeepSeek-V4.1-Flash</span>
          </span>
        </div>
      </div>

      {/* Model & Endpoint Settings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Endpoint */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1">
            <Globe className="w-3.5 h-3.5 text-sky-400" />
            <span>عنوان الخدمة (API Base URL)</span>
          </label>
          <input
            type="text"
            value={aiConfig.apiBase}
            onChange={(e) => onChange({ ...aiConfig, apiBase: e.target.value.trim() })}
            dir="ltr"
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono"
          />
        </div>

        {/* Primary Model */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            النموذج الأساسي (Primary Model)
          </label>
          <select
            value={aiConfig.primaryModel}
            onChange={(e) => onChange({ ...aiConfig, primaryModel: e.target.value })}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono"
          >
            <option value="DeepSeek-V4.1-Flash">DeepSeek-V4.1-Flash (يدعم البحث مدمجاً)</option>
            <option value="DeepSeek-V4-Flash">DeepSeek-V4-Flash</option>
            <option value="DeepSeek-V4-Pro">DeepSeek-V4-Pro</option>
            <option value="auto">auto (توجيه تلقائي)</option>
            <option value="glm-5.3-flash">glm-5.3-flash</option>
          </select>
        </div>

        {/* Fallback Model */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            النموذج البديل عند الضغط (Fallback)
          </label>
          <select
            value={aiConfig.fallbackModel}
            onChange={(e) => onChange({ ...aiConfig, fallbackModel: e.target.value })}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono"
          >
            <option value="auto">auto (يوجّه تلقائياً للنموذج الأنسب)</option>
            <option value="DeepSeek-V4-Flash">DeepSeek-V4-Flash</option>
            <option value="glm-5.3-flash">glm-5.3-flash</option>
          </select>
        </div>
      </div>

      {/* Custom User Instructions Field */}
      <div className="space-y-2 p-4 bg-slate-950/60 rounded-xl border border-slate-800">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
            <Wand2 className="w-4 h-4 text-amber-400" />
            <span>مجال التعليمات المخصصة للمشرف (يتم تطبيقها بالحرف الواحد):</span>
          </label>
          <span className="text-[11px] text-slate-500 font-mono">
            {aiConfig.customInstructions.length} حرفاً
          </span>
        </div>

        <textarea
          rows={3}
          value={aiConfig.customInstructions}
          onChange={(e) => onChange({ ...aiConfig, customInstructions: e.target.value })}
          placeholder="اكتب هنا أي تعليمات تريد من الذكاء الاصطناعي الالتزام بها (مثال: كن مثل مشرفين القروبات الذي يبحث عن الأخبار للطلاب، ركز على المواعيد، لا تذكر مصدر الخبر)..."
          className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs sm:text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500 leading-relaxed font-sans"
        />

        {/* Presets */}
        <div className="space-y-1.5 pt-1">
          <span className="block text-[11px] font-semibold text-slate-400">نماذج تعليمات سريعة جاهزة:</span>
          <div className="flex flex-wrap gap-2">
            {presetInstructions.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onChange({ ...aiConfig, customInstructions: p.text })}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-700 transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* System Prompt View Toggle */}
      <div className="pt-2">
        <button
          type="button"
          onClick={() => setShowSystemPrompt(!showSystemPrompt)}
          className="text-xs text-sky-400 hover:underline flex items-center gap-1 font-semibold"
        >
          <FileCode className="w-3.5 h-3.5" />
          <span>{showSystemPrompt ? 'إخفاء نص التوجيه الأساسي (System Prompt)' : 'عرض نص التوجيه الأساسي (System Prompt) المضمن'}</span>
        </button>

        {showSystemPrompt && (
          <div className="mt-3 p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
            {aiConfig.systemPrompt}
          </div>
        )}
      </div>
    </div>
  );
};
