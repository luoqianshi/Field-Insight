<script setup lang="ts">
/**
 * 地理位置信息编辑器：地图选点 / 从架次图片 EXIF 提取 / 手动清除。
 * v-model 绑定 { latitude, longitude, altitude_m, geo_source }（WGS84 十进制度）。
 */
import { ref, computed } from 'vue'
import Icon from '@/components/common/Icon.vue'
import GeoMapModal from './GeoMapModal.vue'
import { geoApi } from '@/api/batches'

export interface GeoValue {
  latitude?: number | null
  longitude?: number | null
  altitude_m?: number | null
  geo_source?: string
}

const props = defineProps<{
  modelValue: GeoValue
  /** 架次图片文件夹路径，用于 EXIF 提取；为空时禁用提取按钮 */
  folderPath?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: GeoValue): void
}>()

const mapOpen = ref(false)
const extracting = ref(false)
const hint = ref('')
const hintType = ref<'ok' | 'warn'>('ok')

const hasCoords = computed(
  () => typeof props.modelValue.latitude === 'number' && typeof props.modelValue.longitude === 'number',
)

const sourceLabel = computed(() => {
  switch (props.modelValue.geo_source) {
    case 'map_pick': return '地图选点'
    case 'image_exif': return '图片 EXIF'
    default: return '手动'
  }
})

const coordText = computed(() => {
  if (!hasCoords.value) return ''
  const lat = (props.modelValue.latitude as number).toFixed(7)
  const lng = (props.modelValue.longitude as number).toFixed(7)
  return `${lat}, ${lng}`
})

function onMapConfirm(payload: { latitude: number; longitude: number }) {
  emit('update:modelValue', {
    latitude: payload.latitude,
    longitude: payload.longitude,
    altitude_m: props.modelValue.altitude_m ?? null,
    geo_source: 'map_pick',
  })
  hint.value = '已通过地图选点设置坐标'
  hintType.value = 'ok'
  mapOpen.value = false
}

async function extractFromImages() {
  if (!props.folderPath || extracting.value) return
  extracting.value = true
  hint.value = ''
  try {
    const res = await geoApi.extractFromImages(props.folderPath)
    const r = res.data
    if (r.found) {
      emit('update:modelValue', {
        latitude: r.latitude,
        longitude: r.longitude,
        altitude_m: r.altitude_m,
        geo_source: 'image_exif',
      })
      hint.value = r.message
      hintType.value = 'ok'
    } else {
      hint.value = r.message || '未在图片中找到 GPS 信息'
      hintType.value = 'warn'
    }
  } catch (e: any) {
    hint.value = e.message || '提取失败'
    hintType.value = 'warn'
  } finally {
    extracting.value = false
  }
}

function clearGeo() {
  emit('update:modelValue', { latitude: null, longitude: null, altitude_m: null, geo_source: '' })
  hint.value = '已清除地理位置'
  hintType.value = 'ok'
}
</script>

<template>
  <div class="space-y-2">
    <!-- 已设置坐标：展示 -->
    <div v-if="hasCoords" class="bg-surface-bg rounded-btn p-3">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <Icon name="map-pin" :size="14" class="text-brand-700 flex-shrink-0" />
          <span class="text-sm font-mono text-ink-primary truncate">{{ coordText }}</span>
          <span class="tag tag-green flex-shrink-0">{{ sourceLabel }}</span>
        </div>
        <div class="flex items-center gap-1.5 flex-shrink-0">
          <button type="button" @click="mapOpen = true" class="text-xs text-brand-700 hover:underline">重新选点</button>
          <span class="text-xs text-ink-tertiary">·</span>
          <button type="button" @click="clearGeo" class="text-xs text-ink-tertiary hover:text-red-600">清除</button>
        </div>
      </div>
      <div class="mt-1.5 text-xs text-ink-tertiary flex items-center gap-3">
        <span>坐标系：WGS84（EPSG:4326，十进制度）</span>
        <span v-if="modelValue.altitude_m != null">海拔：{{ modelValue.altitude_m }} m</span>
      </div>
    </div>

    <!-- 未设置：操作按钮 -->
    <div v-else class="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        @click="mapOpen = true"
        class="px-3 py-1.5 bg-white border border-surface-border hover:bg-surface-hover text-brand-700 rounded-btn text-xs font-medium inline-flex items-center gap-1.5"
      >
        <Icon name="map-pin" :size="12" /> 地图选点
      </button>
      <button
        type="button"
        @click="extractFromImages"
        :disabled="!folderPath || extracting"
        class="px-3 py-1.5 bg-white border border-surface-border hover:bg-surface-hover disabled:opacity-50 text-brand-700 rounded-btn text-xs font-medium inline-flex items-center gap-1.5"
        :title="folderPath ? '抽样读取图片 EXIF 中的无人机 GPS' : '请先填写并扫描图片文件夹路径'"
      >
        <Icon name="image" :size="12" /> {{ extracting ? '提取中…' : '从图片 EXIF 提取' }}
      </button>
      <span v-if="!folderPath" class="text-xs text-ink-tertiary">
        <Icon name="info" :size="12" class="inline" /> 填写图片路径后可自动提取拍摄定位
      </span>
    </div>

    <p v-if="hint" class="text-xs" :class="hintType === 'ok' ? 'text-brand-700' : 'text-amber-600'">
      <Icon :name="hintType === 'ok' ? 'check-circle' : 'info'" :size="12" class="inline" /> {{ hint }}
    </p>

    <GeoMapModal
      v-if="mapOpen"
      :initial-latitude="modelValue.latitude"
      :initial-longitude="modelValue.longitude"
      @confirm="onMapConfirm"
      @close="mapOpen = false"
    />
  </div>
</template>
