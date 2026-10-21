export type SourceType = 'telegram' | 'twitter' | 'rss';
export type SourcePriority = 'high' | 'medium' | 'low';
export type SourceRule = 'official' | 'semi-official'; // [رسمي] أو [شبه رسمي]

export interface SourceItem {
  id: string;
  type: SourceType;
  target: string; // e.g. @KSU_News or https://site.edu/rss or user_id
  title: string;
  priority: SourcePriority;
  rule: SourceRule;
  keywords: string[];
  blacklist: string[];
  enabled: boolean;
  lastPostId: string;
  lastChecked?: string;
}

export interface SourcesConfig {
  _info?: string;
  version?: string;
  lastUpdated?: string;
  sources: SourceItem[];
}

export interface AIModelConfig {
  apiBase: string; // https://api.hcnsec.cn/v1
  apiKey: string; // sk-J2ky44F6...
  primaryModel: string; // DeepSeek-V4.1-Flash
  fallbackModel: string; // auto
  systemPrompt: string;
  customInstructions: string;
  enableWebSearch: boolean;
}

export interface AdReplacementConfig {
  enabled: boolean;
  adDetectionKeywords: string[];
  customStudentAd: string;
}

export interface BotConfig {
  botToken: string;
  adminId: string;
  adminUsername: string;
  additionalAdminIds: string[];
  notifyAdminOnForward: boolean;
  enableTelegramAdminCommands: boolean;
  preferredEngine: 'bot' | 'telethon';
  ai: AIModelConfig;
  adReplacement: AdReplacementConfig;
  telethon: {
    apiId: string;
    apiHash: string;
    phoneNumber: string;
    sessionName: string;
  };
}

export interface BotInfo {
  id: number;
  is_bot: boolean;
  first_name: string;
  username: string;
  can_join_groups?: boolean;
  can_read_all_group_messages?: boolean;
  supports_inline_queries?: boolean;
}

export interface ForwardRule {
  id: string;
  name: string;
  enabled: boolean;
  sourceChatId: string;
  sourceChatTitle?: string;
  destinationChatId: string;
  destinationChatTitle?: string;
  matchType: 'all' | 'any' | 'none';
  keywords: string[];
  blacklistKeywords: string[];
  caseSensitive: boolean;
  replaceRules: {
    find: string;
    replaceWith: string;
  }[];
  removeLinks: boolean;
  removeUsernames: boolean;
  customSignature: string;
  forwardMode: 'copy' | 'quote';
  delaySeconds: number;
  mediaFilter: {
    allowText: boolean;
    allowPhotos: boolean;
    allowVideos: boolean;
    allowDocuments: boolean;
    allowAudio: boolean;
  };
}

export interface ActivityLogItem {
  id: string;
  timestamp: string;
  type: 'success' | 'filtered' | 'error' | 'info';
  messageText: string;
  source: string;
  destination: string;
  details: string;
  appliedRuleName?: string;
}

export interface MessageSimulationResult {
  accepted: boolean;
  reason: string;
  originalText: string;
  transformedText: string;
  matchedKeywords: string[];
  triggeredBlacklist: string[];
  mediaAllowed: boolean;
  isAdReplaced?: boolean;
}
