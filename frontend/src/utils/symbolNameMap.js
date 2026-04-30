export const CORE_SYMBOL_NAME_MAP = {
  '510300': '沪深300ETF',
  '510500': '中证500ETF',
  '515180': '红利ETF',
  '518880': '黄金ETF',
  '600519': '贵州茅台',
  '000858': '五粮液',
  '600036': '招商银行',
  '000333': '美的集团',
  '601318': '中国平安',
};

function normalizeText(value) {
  if (value === undefined || value === null) {
    return '';
  }
  return String(value).trim();
}

export function mergeSymbolNameMaps(...maps) {
  return maps.reduce((acc, current) => {
    if (!current || typeof current !== 'object') {
      return acc;
    }
    Object.entries(current).forEach(([symbol, name]) => {
      const normalizedName = normalizeText(name);
      if (!normalizedName) {
        return;
      }
      acc[String(symbol)] = normalizedName;
    });
    return acc;
  }, {});
}

export function buildSymbolNameMapFromPortfolioConfig(portfolioConfig) {
  const map = {};
  const etfPool = Array.isArray(portfolioConfig?.etf_pool) ? portfolioConfig.etf_pool : [];
  const stockPool = Array.isArray(portfolioConfig?.stock_pool) ? portfolioConfig.stock_pool : [];
  const items = [...etfPool, ...stockPool];

  items.forEach((item) => {
    const symbol = normalizeText(item?.symbol);
    const name = normalizeText(item?.name || item?.display_name || item?.symbol_name);
    if (!symbol || !name) {
      return;
    }
    map[symbol] = name;
  });

  return map;
}

export function pickDisplayName(symbol, candidates = [], symbolNameMap = {}) {
  const normalizedSymbol = normalizeText(symbol);
  const candidate = candidates
    .map((value) => normalizeText(value))
    .find((value) => Boolean(value) && value !== 'N/A');

  if (candidate) {
    return candidate;
  }

  if (normalizedSymbol && symbolNameMap[normalizedSymbol]) {
    return symbolNameMap[normalizedSymbol];
  }

  if (normalizedSymbol && CORE_SYMBOL_NAME_MAP[normalizedSymbol]) {
    return CORE_SYMBOL_NAME_MAP[normalizedSymbol];
  }

  return '';
}

export function buildSymbolDisplayTitle(symbol, displayName) {
  const normalizedSymbol = normalizeText(symbol);
  const normalizedName = normalizeText(displayName);
  if (normalizedSymbol && normalizedName) {
    return `${normalizedSymbol} / ${normalizedName}`;
  }
  return normalizedSymbol || normalizedName || 'N/A';
}

