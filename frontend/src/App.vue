<script>
import { TOKEN_KEY } from './utils/config'

export default {
  onLaunch() {
    // 未登录且不在登录页 → 跳登录页
    const token = uni.getStorageSync(TOKEN_KEY)
    if (!token) {
      uni.reLaunch({ url: '/pages/login/login' })
    }
    // H5 桌面端隐藏原生 TabBar，改用侧边栏导航
    // #ifdef H5
    if (window.innerWidth >= 768) {
      setTimeout(() => uni.hideTabBar({ animation: false }), 200)
    }
    // #endif
  },
  onShow() {
    // #ifdef H5
    if (window.innerWidth >= 768) {
      uni.hideTabBar({ animation: false })
    }
    // #endif
  },
}
</script>

<style>
/* 全局样式（三端通用，rpx 自适应） */
page {
  background: #f3f6fb;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif;
  color: #1e293b;
  font-size: 28rpx;
}

/* H5 桌面端隐藏原生 TabBar，改用侧边栏导航 */
/* #ifdef H5 */
@media (min-width: 768px) {
  uni-tabbar { display: none !important; }
}
/* #endif */

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin: 20rpx 24rpx;
  box-shadow: 0 4rpx 16rpx rgba(22, 104, 220, 0.06);
}

.btn-primary {
  background: linear-gradient(135deg, #1668dc, #3b82f6);
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

.tag {
  display: inline-block;
  font-size: 20rpx;
  padding: 4rpx 14rpx;
  border-radius: 8rpx;
  color: #fff;
  line-height: 1.6;
}

.text-muted { color: #94a3b8; font-size: 24rpx; }
.text-income { color: #16a34a; font-weight: 600; }
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
