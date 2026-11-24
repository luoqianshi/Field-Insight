<script setup lang="ts">
/**
 * 地图选点弹窗：Leaflet 交互式地图，点击放置标记提取 WGS84 经纬度（EPSG:4326）。
 * 支持卫星影像（Esri World Imagery）/ 街道地图（OSM）底图切换与坐标手动定位。
 */
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Icon from '@/components/common/Icon.vue'

const props = defineProps<{
  initialLatitude?: number | null
  initialLongitude?: number | null
}>()

const emit = defineEmits<{
  (e: 'confirm', payload: { latitude: number; longitude: number }): void
  (e: 'close'): void
}>()

const DEFAULT_CENTER: [number, number] = [23.13, 113.27]
const DEFAULT_ZOOM = 12

const mapEl = ref<HTMLDivElement | null>(null)
const latInput = ref('')
const lngInput = ref('')
const baseLayer = ref<'satellite' | 'street'>('satellite')
const locateError = ref('')
let map: L.Map | null = null
let marker: L.Marker | null = null

const hasSelection = computed(() => latInput.value !== '' && lngInput.value !== '')

function parseCoord(raw: string): number | null {
  const v = Number(String(raw).trim())
  return Number.isFinite(v) ? v : null
}

function syncInputs(lat: number, lng: number) {
  latInput.value = lat.toFixed(7)
  lngInput.value = lng.toFixed(7)
}

function setMarker(lat: number, lng: number) {
  if (!map) return
  const icon = L.divIcon({
    className: '',
    html: '<svg width="28" height="36" viewBox="0 0 28 36" xmlns="http://www.w3.org/2000/svg"><path d="M14 35 C14 35 2.5 20.5 2.5 13 A11.5 11.5 0 0 1 25.5 13 C25.5 20.5 14 35 14 35 Z" fill="#10B981" stroke="#065F46" stroke-width="1.5"/><circle cx="14" cy="13" r="4.2" fill="#fff"/></svg>',
    iconSize: [28, 36],
    iconAnchor: [14, 35],
  })
  if (marker) marker.setLatLng([lat, lng])
  else marker = L.marker([lat, lng], { icon, draggable: true }).addTo(map)
  marker.on('dragend', () => {
    if (!marker) return
    const p = marker.getLatLng()
    syncInputs(p.lat, p.lng)
  })
  syncInputs(lat, lng)
  locateError.value = ''
}

function switchBaseLayer(target: 'satellite' | 'street') {
  baseLayer.value = target
  if (!map) return
  if (satLayer) map.removeLayer(satLayer)
  if (streetLayer) map.removeLayer(streetLayer)
  if (target === 'satellite') satLayer?.addTo(map)
  else streetLayer?.addTo(map)
}

let satLayer: L.TileLayer | null = null
let streetLayer: L.TileLayer | null = null

function doLocate() {
  const lat = parseCoord(latInput.value)
  const lng = parseCoord(lngInput.value)
  if (lat === null || lng === null) {
    locateError.value = '请输入有效的十进制度坐标（如 23.1370389）'
    return
  }
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    locateError.value = '纬度范围 -90~90，经度范围 -180~180'
    return
  }
  map?.setView([lat, lng], Math.max(map.getZoom(), 15))
  setMarker(lat, lng)
}

function confirmPick() {
  if (!hasSelection.value) return
  emit('confirm', { latitude: Number(latInput.value), longitude: Number(lngInput.value) })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(async () => {
  await nextTick()
  if (!mapEl.value) return
  const hasInitial =
    typeof props.initialLatitude === 'number' && typeof props.initialLongitude === 'number'
  const center: [number, number] = hasInitial
    ? [props.initialLatitude as number, props.initialLongitude as number]
    : DEFAULT_CENTER

  map = L.map(mapEl.value, { center, zoom: hasInitial ? 16 : DEFAULT_ZOOM, attributionControl: true })
  satLayer = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' },
  )
  streetLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors',
  })
  satLayer.addTo(map)
  map.on('click', (e: L.LeafletMouseEvent) => setMarker(e.latlng.lat, e.latlng.lng))
  if (hasInitial) setMarker(center[0], center[1])
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  map?.remove()
  map = null
})
</script>

<template>
  <div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" @click.self="emit('close')">
    <div class="bg-white rounded-card w-full max-w-4xl flex flex-col overflow-hidden shadow-lg">
      <!-- 头部 -->
      <div class="flex items-center justify-between px-5 py-3 border-b border-surface-border">
        <div class="flex items-center gap-2">
          <Icon name="map-pin" :size="16" class="text-brand-700" />
          <h3 class="text-sm font-semibold text-ink-primary">地图选点（WGS84 / EPSG:4326）</h3>
        </div>
        <div class="flex items-center gap-2">
          <div class="flex border border-surface-border rounded-btn overflow-hidden text-xs">
            <button
              type="button"
              @click="switchBaseLayer('satellite')"
              class="px-3 py-1.5"
              :class="baseLayer === 'satellite' ? 'bg-brand-700 text-white' : 'bg-white text-ink-secondary hover:bg-surface-hover'"
            >卫星影像</button>
            <button
              type="button"
              @click="switchBaseLayer('street')"
              class="px-3 py-1.5 border-l border-surface-border"
              :class="baseLayer === 'street' ? 'bg-brand-700 text-white' : 'bg-white text-ink-secondary hover:bg-surface-hover'"
            >街道地图</button>
          </div>
          <button type="button" @click="emit('close')" class="p-1.5 text-ink-tertiary hover:text-ink-primary" title="关闭">
            <Icon name="close" :size="16" />
          </button>
        </div>
      </div>

      <!-- 地图 -->
      <div ref="mapEl" class="h-[440px] w-full bg-surface-bg"></div>

      <!-- 底部操作栏 -->
      <div class="px-5 py-3 border-t border-surface-border">
        <div class="flex items-end gap-3 flex-wrap">
          <div class="flex-1 min-w-[140px]">
            <label class="block text-xs font-medium text-ink-primary mb-1">纬度（°N）</label>
            <input v-model="latInput" type="text" placeholder="23.1370389" class="w-full px-3 py-2 bg-white border border-surface-border rounded-btn text-sm font-mono focus:outline-none focus:border-brand-300" />
          </div>
          <div class="flex-1 min-w-[140px]">
            <label class="block text-xs font-medium text-ink-primary mb-1">经度（°E）</label>
            <input v-model="lngInput" type="text" placeholder="113.2638889" class="w-full px-3 py-2 bg-white border border-surface-border rounded-btn text-sm font-mono focus:outline-none focus:border-brand-300" />
          </div>
          <button type="button" @click="doLocate" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover text-ink-primary rounded-btn text-sm">
            <Icon name="target" :size="12" class="inline mr-1" />定位到坐标
          </button>
          <div class="flex-1"></div>
          <button type="button" @click="emit('close')" class="px-4 py-2 bg-white border border-surface-border hover:bg-surface-hover text-ink-primary rounded-btn text-sm">取消</button>
          <button
            type="button"
            @click="confirmPick"
            :disabled="!hasSelection"
            class="px-4 py-2 bg-brand-700 hover:bg-brand-900 disabled:opacity-50 text-white rounded-btn text-sm font-medium"
          >确认选点</button>
        </div>
        <p v-if="locateError" class="text-xs text-red-600 mt-2">{{ locateError }}</p>
        <p v-else class="text-xs text-ink-tertiary mt-2">
          <Icon name="info" :size="12" class="inline" />
          在地图上单击放置标记（可拖拽微调），或直接输入坐标后点「定位到坐标」；坐标为 WGS84 十进制度
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Leaflet 容器字体与浅色主题对齐 */
:deep(.leaflet-container) {
  font-family: inherit;
  font-size: 12px;
}
</style>
