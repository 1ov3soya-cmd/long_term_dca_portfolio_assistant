/**
 * 把空值统一降级成占位文本。
 */
export function fallbackText(value, placeholder = 'N/A') {
  if (value === undefined || value === null || value === '') {
    return placeholder;
  }
  return String(value);
}

/**
 * 数字金额格式化。
 */
export function formatCurrency(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return 'N/A';
  }

  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

/**
 * 百分比字符串格式化。
 */
export function formatPercent(value, digits = 1) {
  if (value === undefined || value === null || value === '' || Number.isNaN(Number(value))) {
    return 'N/A';
  }

  return `${(Number(value) * 100).toFixed(digits)}%`;
}

/**
 * 列表展示格式化。
 */
export function joinSymbols(values, placeholder = '暂无数据') {
  if (!Array.isArray(values) || values.length === 0) {
    return placeholder;
  }
  return values.join(', ');
}

/**
 * 运行 ID 缩写，保留前部可读性。
 */
export function compactRunId(value, maxLength = 18) {
  if (!value || value === 'N/A') {
    return 'N/A';
  }
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength)}...`;
}
