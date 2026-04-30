const ROLE_OPENING_PATTERNS = [
  /^bull\s+researcher(?:\s*的立场是)?\s*[：:]\s*/i,
  /^bear\s+researcher(?:\s*的立场是)?\s*[：:]\s*/i,
  /^bull\s+researcher\b[\s，,。:：-]*/i,
  /^bear\s+researcher\b[\s，,。:：-]*/i,
  /^(看多|看空)\s*研究员(?:的立场是)?\s*[：:]\s*/,
];

function normalizeText(value) {
  if (value === undefined || value === null) {
    return '';
  }
  return String(value);
}

export function sanitizeDebateText(value, options = {}) {
  const { removeRoleOpening = false } = options;
  let text = normalizeText(value)
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  if (!text) {
    return '';
  }

  if (removeRoleOpening) {
    ROLE_OPENING_PATTERNS.forEach((pattern) => {
      text = text.replace(pattern, '');
    });
    text = text.replace(/^[：:，,\-。\s]+/, '').trim();
  }

  return text;
}

export function buildDebatePreview(value, maxLength = 120) {
  const cleaned = sanitizeDebateText(value, { removeRoleOpening: true }).replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return '';
  }

  const sentences = cleaned
    .split(/[。！？!?；;]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  let preview = sentences.slice(0, 2).join('。').trim();
  if (!preview) {
    preview = cleaned;
  }

  if (preview.length > maxLength) {
    return `${preview.slice(0, maxLength - 3).trim()}...`;
  }
  return preview;
}

function inferEtfRoleHint(symbol) {
  if (symbol === '510300') {
    return '宽基核心底仓';
  }
  if (symbol === '510500') {
    return '中盘补充底仓';
  }
  if (symbol === '515180') {
    return '红利风格底仓';
  }
  if (symbol === '518880') {
    return '黄金防守底仓';
  }
  return 'ETF配置底仓';
}

function formatAmount(value) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) {
    return '0';
  }
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: number % 1 === 0 ? 0 : 2,
  }).format(number);
}

/**
 * 为 ETF 生成更可读的首页/列表预览文案，避免“占位感”过强。
 */
export function buildEtfDebatePreviewPack(item = {}) {
  const symbol = String(item.symbol || '');
  const name = String(item.displayName || symbol || 'ETF');
  const roleHint = inferEtfRoleHint(symbol);
  const amountText = formatAmount(item.suggestedAmount);

  return {
    bullPreview: `${name}定位为${roleHint}。当前建议金额¥${amountText}，在未触发更高风险前可按既定节奏跟踪。`,
    bearPreview: `若${name}出现价格红线升级或人工复核信号，应先暂停新增并人工复核，避免将配置仓当作进攻仓。`,
    riskPreview: `核心不确定性是风险信号是否持续升级；若升级，先执行风控治理，再评估后续新增。`,
  };
}
