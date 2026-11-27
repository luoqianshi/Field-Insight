<script setup lang="ts">
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps<{
  page: number
  pageSize: number
  total: number
}>()

const emit = defineEmits<{ (e: 'update:page', value: number): void }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const start = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const end = computed(() => Math.min(props.total, props.page * props.pageSize))

// 页码窗口：当前页前后各一页 + 首尾页，间隙以省略号衔接
const pages = computed<(number | 'ellipsis')[]>(() => {
  const n = totalPages.value
  const cur = Math.min(props.page, n)
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1)
  const picked = new Set<number>([1, n, cur - 1, cur, cur + 1])
  const arr: (number | 'ellipsis')[] = []
  let prev = 0
  for (const p of Array.from(picked)
    .filter((v) => v >= 1 && v <= n)
    .sort((a, b) => a - b)) {
    if (prev && p - prev > 1) arr.push('ellipsis')
    arr.push(p)
    prev = p
  }
  return arr
})

function go(p: number) {
  if (p < 1 || p > totalPages.value || p === props.page) return
  emit('update:page', p)
}
</script>

<template>
  <div class="flex items-center justify-between px-5 py-2.5">
    <div class="text-xs text-ink-tertiary">
      共 <span class="font-numeric text-ink-secondary">{{ total }}</span> 条 · 显示
      <span class="font-numeric text-ink-secondary">{{ start }}-{{ end }}</span> 条 · 第
      <span class="font-numeric text-ink-secondary">{{ page }}</span>/
      <span class="font-numeric text-ink-secondary">{{ totalPages }}</span> 页
    </div>
    <div class="flex items-center gap-1">
      <button
        :disabled="page <= 1"
        class="h-7 w-7 inline-flex items-center justify-center rounded-btn border border-surface-border bg-white text-ink-secondary hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="上一页"
        @click="go(page - 1)"
      >
        <Icon name="chevron-left" :size="13" />
      </button>
      <template v-for="(p, i) in pages" :key="`${p}-${i}`">
        <span v-if="p === 'ellipsis'" class="h-7 px-1 inline-flex items-center text-xs text-ink-tertiary">…</span>
        <button
          v-else
          class="h-7 min-w-[28px] px-1 inline-flex items-center justify-center rounded-btn border text-xs font-numeric"
          :class="
            p === page
              ? 'bg-brand-700 border-brand-700 text-white'
              : 'bg-white border-surface-border text-ink-secondary hover:bg-surface-hover'
          "
          @click="go(p)"
        >
          {{ p }}
        </button>
      </template>
      <button
        :disabled="page >= totalPages"
        class="h-7 w-7 inline-flex items-center justify-center rounded-btn border border-surface-border bg-white text-ink-secondary hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="下一页"
        @click="go(page + 1)"
      >
        <Icon name="chevron-right" :size="13" />
      </button>
    </div>
  </div>
</template>
