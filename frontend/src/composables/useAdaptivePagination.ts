import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'

interface AdaptivePaginationOptions {
  /** 列表卡片容器元素，用于测量可用高度 */
  target: Ref<HTMLElement | null>
  /** 数据行选择器，用于实测单行高度（须排除加载中/空态等占位行） */
  rowSelector?: string
  /** 实测失败时的兜底行高（px） */
  fallbackRowHeight?: number
  /** 列表底部预留高度（分页条 / 提示行 / 边距，px） */
  reservePx?: number
  /** 单页最少行数 */
  minPageSize?: number
  /** 单页最多行数 */
  maxPageSize?: number
}

const DEFAULTS = {
  rowSelector: 'tr.data-row',
  fallbackRowHeight: 66,
  /** 分页条 + 底部提示行 + 边距的预留高度 */
  reservePx: 92,
  minPageSize: 2,
  maxPageSize: 50,
}

/**
 * 自适应分页：按视口可容纳的行数动态计算每页条数。
 * 数据行数不超过单页容量时不分页（维持整表展示）；
 * 超出时切换为底部分页模式，整页内容控制在一屏内，无需滚动即可翻页浏览。
 */
export function useAdaptivePagination<T>(items: Ref<T[]>, options: AdaptivePaginationOptions) {
  const opts = { ...DEFAULTS, ...options }

  const page = ref(1)
  const pageSize = ref(opts.minPageSize)
  const rowHeight = ref(opts.fallbackRowHeight)

  const total = computed(() => items.value.length)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
  /** 行数超出单屏可容纳行数时切换为分页模式 */
  const paginated = computed(() => total.value > pageSize.value)
  const pageItems = computed(() => {
    if (!paginated.value) return items.value
    const start = (page.value - 1) * pageSize.value
    return items.value.slice(start, start + pageSize.value)
  })
  /** 分页模式下锁定卡片最小高度，翻页时顶部内容与底部分页条不跳动 */
  const cardMinHeight = computed(() =>
    paginated.value ? `${pageSize.value * rowHeight.value + 102}px` : undefined,
  )

  function findScrollParent(el: HTMLElement): HTMLElement | null {
    let p = el.parentElement
    while (p) {
      const oy = getComputedStyle(p).overflowY
      if (oy === 'auto' || oy === 'scroll' || oy === 'overlay') return p
      p = p.parentElement
    }
    return null
  }

  function measure() {
    const el = opts.target.value
    if (!el || !el.isConnected) return
    const row = el.querySelector<HTMLElement>(opts.rowSelector)
    if (row && row.offsetHeight > 0) rowHeight.value = row.offsetHeight
    // 列表卡片顶边在滚动容器可视区内的高位（滚动不变量，翻页/滚动后测量仍准确）
    const scrollParent = findScrollParent(el)
    const topWithin = scrollParent
      ? el.getBoundingClientRect().top -
        scrollParent.getBoundingClientRect().top +
        scrollParent.scrollTop
      : el.getBoundingClientRect().top
    const viewport = scrollParent ? scrollParent.clientHeight : window.innerHeight
    const theadH = el.querySelector<HTMLElement>('thead')?.offsetHeight ?? 48
    const usable = viewport - topWithin - theadH - opts.reservePx
    if (usable <= 0) return
    const size = Math.floor(usable / rowHeight.value)
    pageSize.value = Math.min(opts.maxPageSize, Math.max(opts.minPageSize, size))
  }

  function goTo(p: number) {
    page.value = Math.min(Math.max(1, p), totalPages.value)
  }

  watch(
    () => items.value.length,
    () => {
      page.value = 1
    },
  )
  watch(pageSize, () => {
    if (page.value > totalPages.value) page.value = totalPages.value
  })
  watch(total, () => nextTick(measure))

  const onResize = () => measure()
  onMounted(() => {
    measure()
    window.addEventListener('resize', onResize)
  })
  onBeforeUnmount(() => window.removeEventListener('resize', onResize))

  return { page, pageSize, totalPages, total, paginated, pageItems, cardMinHeight, goTo, measure }
}
