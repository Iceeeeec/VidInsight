/**
 * 标题: PM2 配置文件
 * 说明: VidInsight 应用的 PM2 进程管理配置
 * 时间: 2026-01-14
 * @author: zhoujunyu
 */

module.exports = {
  apps: [
    {
      name: 'vidinsight',
      script: 'streamlit',
      args: 'run app.py --server.port 8501 --server.address 0.0.0.0',
      interpreter: 'none',
      cwd: '/root/SummaView',  // 服务器上的项目路径，根据实际情况修改
      env: {
        NODE_ENV: 'production'
      },
      // 日志配置
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: './logs/error.log',
      out_file: './logs/out.log',
      merge_logs: true,
      // 自动重启配置
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      // 监控配置
      watch: false,
      max_memory_restart: '500M'
    }
  ]
};
