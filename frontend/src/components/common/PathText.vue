<script setup lang="ts">
import { computed, ref } from 'vue'

// 长路径缩略显示：默认仅保留末两级（前缀缩为 …/），单行截断防溢出；
// 悬停 title 提示完整路径，点击切换展开/收起完整路径。
const props = withDefaults(
  defineProps<{ path?: string | null; fallback?: string }>(),
  { path: '', fallback: '-' },
)

const expanded = ref(false)
const full = computed(() => (props.path || '').trim() || props.fallback)
const segments = computed(() => full.value.split(/[\\/]+/).filter(Boolean))
const short = computed(() =>
  segments.value.length > 2 ? '…/' + segments.value.slice(-2).join('/') : full.value,
)
const collapsible = computed(() => short.value !== full.value)

function toggle() {
  if (collapsible.value) expanded.value = !expanded.value
}
</script>

<template>
  <span
    :title="full"
    :class="[
      'min-w-0',
      collapsible ? 'cursor-pointer' : '',
      expanded ? 'block whitespace-normal break-all' : 'block truncate',
    ]"
    @click.stop="toggle"
  >{{ expanded ? full : short }}</span>
</template>
