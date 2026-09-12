<script>
import { TOKEN_KEY } from './utils/config'

export default {
  onLaunch() {
    const token = uni.getStorageSync(TOKEN_KEY)
    if (!token) {
      uni.reLaunch({ url: '/pages/login/login' })
    }
  },
}
</script>

<style>
/* 全局样式（三端通用，对齐 PC 端设计语言） */
page {
  background: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif;
  color: #1e293b;
  font-size: 28rpx;
}

/* #ifdef H5 */
@media (min-width: 768px) {
  uni-tabbar, .uni-tabbar, .uni-tabbar-bottom, .custom-tab-bar { display: none !important; }
}
/* #endif */

.card {
  background: #fff;
  border-radius: 24rpx;
  padding: 40rpx;
  margin: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}

.btn-primary {
  background: #1e3a8a;
  color: #fff;
  border-radius: 44rpx;
  font-size: 30rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  border: none;
}
.btn-primary::after { border: none; }

.btn-ghost {
  background: #f1f5f9;
  color: #475569;
  border-radius: 44rpx;
  font-size: 28rpx;
  height: 80rpx;
  line-height: 80rpx;
  text-align: center;
}
.btn-ghost::after { border: none; }

/* 市场徽章：浅底深字风格（对齐 PC global.css） */
.tag {
  display: inline-block;
  font-size: 20rpx;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  line-height: 1.6;
  font-weight: 500;
}
.tag-a { background: #fef2f2; color: #dc2626; }
.tag-us { background: #eff6ff; color: #2563eb; }
.tag-hk { background: #ecfdf5; color: #059669; }
.tag-fund { background: #fffbeb; color: #d97706; }
.tag-bond { background: #f5f3ff; color: #7c3aed; }

/* 状态徽章 */
.badge-confirmed { background: #ecfdf5; color: #059669; }
.badge-pending { background: #fffbeb; color: #d97706; }

.text-muted { color: #94a3b8; font-size: 24rpx; }
.text-emerald { color: #059669; font-weight: 600; }
.text-amber { color: #d97706; font-weight: 600; }
.text-income { color: #059669; font-weight: 600; }
.text-pending { color: #d97706; font-weight: 600; }

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1e293b;
  margin: 24rpx 24rpx 8rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-row {
  display: flex;
  align-items: center;
  padding: 24rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
}
.form-label {
  width: 180rpx;
  color: #475569;
  font-size: 28rpx;
  flex-shrink: 0;
}
.form-input {
  flex: 1;
  font-size: 28rpx;
  text-align: right;
}

.empty {
  text-align: center;
  color: #94a3b8;
  padding: 100rpx 0;
  font-size: 26rpx;
}
</style>
