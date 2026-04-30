/**
 * 安全读取嵌套字段，避免 Dashboard 因缺字段直接崩溃。
 */
export function deepGet(target, path, fallback = undefined) {
  if (!target || !path) {
    return fallback;
  }

  const segments = Array.isArray(path) ? path : String(path).split('.');
  let current = target;

  for (const segment of segments) {
    if (current === null || current === undefined || !(segment in current)) {
      return fallback;
    }
    current = current[segment];
  }

  return current ?? fallback;
}

/**
 * 返回第一个非空值。
 */
export function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== '');
}

/**
 * 统一转成数组。
 */
export function toArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === undefined || value === null) {
    return [];
  }
  return [value];
}

/**
 * 判定字符串是否有内容。
 */
export function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim() !== '';
}

/**
 * 对对象数组做过滤计数。
 */
export function countBy(items, predicate) {
  return toArray(items).filter(predicate).length;
}
