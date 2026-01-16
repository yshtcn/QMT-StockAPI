#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据Web服务器
提供目录下所有JSON和CSV数据的访问
支持Bearer Token认证
"""

import os
import json
import csv
import argparse
import secrets
from functools import wraps
from flask import Flask, jsonify, send_file, render_template_string, request, session
from flask_cors import CORS
import pandas as pd
from datetime import datetime
import logging
from typing import List

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域访问

# 设置session密钥
app.secret_key = secrets.token_hex(16)

# 全局变量存储API密钥
API_KEY = None

# 获取数据目录（统一为./data）
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(BASE_DIR, exist_ok=True)

# 即时查询模块（新增）
try:
    from instant_query import perform_instant_update
except Exception as _e:
    perform_instant_update = None
    logger = logging.getLogger(__name__)
    logger.warning(f"instant_query 模块未加载: {_e}")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='股票数据Web服务器')
    parser.add_argument('--api-key', type=str, help='API访问密钥 (Bearer Token)')
    parser.add_argument('--port', type=int, default=8888, help='服务器端口 (默认: 8888)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器地址 (默认: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    return parser.parse_args()

def check_auth():
    """检查认证状态"""
    # 如果没有设置API密钥，则不需要认证
    if not API_KEY:
        return True
    
    # 方式1: Bearer Token (Header)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        if token == API_KEY:
            return True
    
    # 方式2: API Key (Query参数)
    api_key_param = request.args.get('api_key')
    if api_key_param == API_KEY:
        return True
    
    # 方式3: Session认证 (Web界面登录后)
    if session.get('authenticated') == True:
        return True
    
    return False

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_auth():
            # 如果是API请求，返回JSON错误
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': '需要Bearer Token认证',
                    'auth_methods': [
                        'Header: Authorization: Bearer <your-api-key>',
                        'Query: ?api_key=<your-api-key>'
                    ]
                }), 401
            # 如果是Web请求，重定向到登录页面
            else:
                return render_login_page()
        return f(*args, **kwargs)
    return decorated_function

def render_login_page():
    """渲染登录页面"""
    if not API_KEY:
        # 如果没有设置API密钥，直接允许访问
        return index()
    
    # 检查是否是登录提交
    if request.method == 'POST':
        submitted_key = request.form.get('api_key')
        if submitted_key == API_KEY:
            session['authenticated'] = True
            return index()
        else:
            error_msg = "API密钥错误，请重试"
    else:
        error_msg = None
    
    login_template = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>身份验证 - 股票数据服务器</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .auth-container {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
                text-align: center;
            }
            .auth-title {
                color: #333;
                font-size: 24px;
                margin-bottom: 30px;
                font-weight: 600;
            }
            .auth-form {
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 20px;
                text-align: left;
            }
            .form-label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }
            .form-input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            .form-input:focus {
                outline: none;
                border-color: #667eea;
            }
            .auth-button {
                width: 100%;
                padding: 12px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            .auth-button:hover {
                background: #5a67d8;
            }
            .error-message {
                color: #e53e3e;
                margin-top: 15px;
                padding: 10px;
                background: #fed7d7;
                border-radius: 6px;
                border: 1px solid #feb2b2;
            }
            .auth-methods {
                margin-top: 30px;
                padding: 20px;
                background: #f7fafc;
                border-radius: 8px;
                text-align: left;
            }
            .methods-title {
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 10px;
            }
            .method-item {
                margin-bottom: 8px;
                font-family: monospace;
                background: #edf2f7;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
                color: #4a5568;
            }
        </style>
    </head>
    <body>
        <div class="auth-container">
            <h1 class="auth-title">🔐 身份验证</h1>
            
            <form method="POST" class="auth-form">
                <div class="form-group">
                    <label for="api_key" class="form-label">API 密钥</label>
                    <input type="password" id="api_key" name="api_key" class="form-input" 
                           placeholder="请输入API密钥" required autocomplete="current-password">
                </div>
                <button type="submit" class="auth-button">登录</button>
            </form>
            
            {% if error_msg %}
            <div class="error-message">{{ error_msg }}</div>
            {% endif %}
            
            <div class="auth-methods">
                <div class="methods-title">📡 API认证方式：</div>
                <div class="method-item">Bearer Token: Authorization: Bearer &lt;your-key&gt;</div>
                <div class="method-item">Query参数: ?api_key=&lt;your-key&gt;</div>
                <div class="method-item">Web登录: 通过此页面登录</div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    from jinja2 import Template
    template_obj = Template(login_template)
    return template_obj.render(error_msg=error_msg)

def get_data_files():
    """获取数据目录下所有JSON和CSV文件"""
    files = []
    for filename in os.listdir(BASE_DIR):
        if filename.lower().endswith(('.json', '.csv')):
            filepath = os.path.join(BASE_DIR, filename)
            file_size = os.path.getsize(filepath)
            file_info = {
                'name': filename,
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'type': 'JSON' if filename.lower().endswith('.json') else 'CSV',
                'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
            }
            files.append(file_info)
    
    # 按文件名排序
    files.sort(key=lambda x: x['name'])
    return files

def parse_filename(filename):
    """解析文件名获取股票信息"""
    parts = filename.replace('.json', '').replace('.csv', '').split('_')
    if len(parts) >= 3:
        stock_code = parts[0]
        market = parts[1]
        data_type = '_'.join(parts[2:])
        return {
            'stock_code': stock_code,
            'market': market,
            'data_type': data_type
        }
    return {'stock_code': '', 'market': '', 'data_type': filename}

@app.route('/', methods=['GET', 'POST'])
@require_auth
def index():
    """主页 - 显示所有可用的数据文件"""
    files = get_data_files()
    
    # 简单的HTML模板
    template = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>股票数据服务器</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .stats { display: flex; justify-content: space-around; margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 6px; }
            .stat-item { text-align: center; }
            .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
            .stat-label { color: #666; margin-top: 5px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f8f9fa; font-weight: bold; color: #495057; }
            tr:hover { background-color: #f5f5f5; }
            .file-link { color: #007bff; text-decoration: none; font-weight: 500; }
            .file-link:hover { text-decoration: underline; }
            .file-type { padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
            .json-type { background: #e3f2fd; color: #1976d2; }
            .csv-type { background: #e8f5e8; color: #388e3c; }
            .api-info { margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 6px; border-left: 4px solid #ffc107; }
            .api-title { font-weight: bold; color: #856404; margin-bottom: 10px; }
            .api-url { font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 3px; }
            /* 新增：主界面即时查询 API 链接区块 */
            .api-link { margin-top: 10px; padding: 10px; background: #fffbe6; border: 1px solid #ffe58f; border-radius: 6px; font-size: 12px; }
            .api-link .url { width: 100%; box-sizing: border-box; margin-top: 6px; padding: 8px; font-family: monospace; font-size: 12px; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📈 股票数据服务器</h1>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number">{{ total_files }}</div>
                    <div class="stat-label">总文件数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ json_files }}</div>
                    <div class="stat-label">JSON文件</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ csv_files }}</div>
                    <div class="stat-label">CSV文件</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ total_size_mb }}</div>
                    <div class="stat-label">总大小(MB)</div>
                </div>
            </div>
            
            <!-- 顶部即时查询表单（新增） -->
            <div class="container" style="margin-top: 10px; margin-bottom: 10px; padding: 16px; background: #eef2ff; border-radius: 8px;">
                <div style="display:flex; gap:10px; align-items:center; flex-wrap: wrap;">
                    <input id="q_stock" type="text" placeholder="股票代码，如 600689.SH" style="flex:1; min-width:240px; padding:10px; border:2px solid #cbd5e1; border-radius:6px;">
                    <select id="q_mode" style="padding:10px; border:2px solid #cbd5e1; border-radius:6px;">
                        <option value="realtime" selected>即时股价</option>
                        <option value="kline">K线</option>
                    </select>
                    <select id="q_period" style="padding:10px; border:2px solid #cbd5e1; border-radius:6px;">
                        <option value="1m">1m</option>
                        <option value="5m">5m</option>
                        <option value="15m" selected>15m</option>
                        <option value="30m">30m</option>
                        <option value="60m">60m</option>
                        <option value="1d">1d</option>
                        <option value="1w">1w</option>
                        <option value="1M">1M</option>
                    </select>
                    <select id="q_dividend" style="padding:10px; border:2px solid #cbd5e1; border-radius:6px;">
                        <option value="front" selected>前复权</option>
                        <option value="none">不复权</option>
                        <option value="back">后复权</option>
                    </select>
                    <button id="q_btn" style="padding:10px 16px; background:#667eea; color:#fff; border:none; border-radius:6px; cursor:pointer;">查询</button>
                </div>
                <div id="q_info" style="margin-top:8px; color:#555; font-size:13px;">提示：查询会写入 ./data 并返回结果预览，可能耗时数秒。</div>
                <div id="q_links" style="margin-top:8px;"></div>
                <pre id="q_result" style="margin-top:10px; background:#f8fafc; padding:10px; border-radius:6px; font-size:12px; overflow:auto;"></pre>
                <div id="q_api" class="api-link" style="display:none;">
                    <div><strong>可复制API(GET)：</strong><span style="color:#666; font-size:12px;">（将该地址用于程序调用同样查询）</span></div>
                    <input id="q_api_url" class="url" readonly value="" />
                    <div style="margin-top:6px;">
                        <button id="q_copy">复制链接</button>
                        <a id="q_open" href="#" target="_blank" style="margin-left:10px;">新窗口打开</a>
                    </div>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>文件名</th>
                        <th>类型</th>
                        <th>大小</th>
                        <th>股票代码</th>
                        <th>数据类型</th>
                        <th>最后修改</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for file in files %}
                    <tr>
                        <td><strong>{{ file.name }}</strong></td>
                        <td><span class="file-type {{ file.type.lower() }}-type">{{ file.type }}</span></td>
                        <td>{{ file.size_mb }} MB</td>
                        <td>{{ file.info.stock_code }}</td>
                        <td>{{ file.info.data_type }}</td>
                        <td>{{ file.modified }}</td>
                        <td>
                            <a href="/api/files/{{ file.name }}" class="file-link" target="_blank">查看原始数据</a> |
                            <a href="/api/files/{{ file.name }}?format=json" class="file-link" target="_blank">JSON格式</a> |
                            <a href="/api/files/{{ file.name }}?format=json&reverse_time=true" class="file-link" target="_blank">最新在前</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="api-info">
                <div class="api-title">📡 API接口说明：</div>
                <p><strong>文件列表：</strong> <span class="api-url">GET /api/files</span></p>
                <p><strong>获取文件：</strong> <span class="api-url">GET /api/files/&lt;filename&gt;</span></p>
                <p><strong>JSON格式：</strong> <span class="api-url">GET /api/files/&lt;filename&gt;?format=json</span></p>
                <p><strong>限制条数：</strong> <span class="api-url">GET /api/files/&lt;filename&gt;?format=json&limit=100</span> (返回最后100条记录)</p>
                <p><strong>逆转时间排序：</strong> <span class="api-url">GET /api/files/&lt;filename&gt;?format=json&reverse_time=true</span> (最新数据在前)</p>
                <p><strong>组合参数：</strong> <span class="api-url">GET /api/files/&lt;filename&gt;?format=json&reverse_time=true&limit=50</span> (最新50条)</p>
                <p><strong>指定编码：</strong> <span class="api-url">GET /api/files/&lt;filename&gt;?encoding=gb2312</span> (支持gb2312、gbk等编码)</p>
                <p><strong>下载文件：</strong> <span class="api-url">GET /api/download/&lt;filename&gt;</span></p>
                <p><strong>统计信息：</strong> <span class="api-url">GET /api/stats</span></p>
                <p><strong>即时查询页面：</strong> <span class="api-url">GET /instant</span></p>
                <p><strong>即时查询API：</strong> <span class="api-url">POST /api/instant_query</span>（参数：stock_code, dividend_type 可选）</p>
                <p><strong>MCP接口：</strong> <span class="api-url">POST /mcp</span>（JSON-RPC 2.0，支持 tools/list、tools/call、resources/list 等）</p>
            </div>
        <script>
        (function(){
            const btn = document.getElementById('q_btn');
            const stock = document.getElementById('q_stock');
            const mode = document.getElementById('q_mode');
            const period = document.getElementById('q_period');
            const dividend = document.getElementById('q_dividend');
            const info = document.getElementById('q_info');
            const resultEl = document.getElementById('q_result');
            const linksEl = document.getElementById('q_links');
            const apiBox = document.getElementById('q_api');
            const apiUrlEl = document.getElementById('q_api_url');
            const apiOpen = document.getElementById('q_open');
            const apiCopy = document.getElementById('q_copy');

            function switchUI(){
                const m = mode.value;
                period.disabled = (m !== 'kline');
                dividend.disabled = (m !== 'kline');
            }
            mode.addEventListener('change', switchUI);
            switchUI();

            btn.addEventListener('click', async () => {
                const code = (stock.value||'').trim();
                if(!code){ alert('请输入股票代码'); return; }
                btn.disabled = true; resultEl.textContent = '正在查询，请稍候...'; linksEl.innerHTML = '';
                try{
                    // 构造参数：realtime 仅实时；kline 仅该周期K线 + 实时
                    let payload = { stock_code: code, dividend_type: dividend.value, include_realtime: true };
                    if(mode.value === 'realtime'){
                        payload['periods'] = []; // 不拉取任何K线
                    }else{
                        payload['periods'] = [period.value];
                    }
                    const resp = await fetch('/api/instant_query', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                    });
                    const data = await resp.json();
                    if(!resp.ok || !data.success){ resultEl.textContent = '查询失败: ' + (data.message || data.error || '未知错误'); apiBox.style.display='none'; return; }
                    // 链接
                    const kfiles = data.kline_files || {}; const list=[];
                    for(const [p, fname] of Object.entries(kfiles)){
                        const url = `/api/files/${fname}?format=json&reverse_time=true&limit=50`;
                        list.push(`<a href="${url}" target="_blank">${p} 最近50条</a>`);
                    }
                    linksEl.innerHTML = list.join(' | ');
                    const show = { stock_code: data.stock_code, mode: mode.value, realtime: data.realtime_data, previews: data.kline_preview };
                    resultEl.textContent = JSON.stringify(show, null, 2);

                    // 构造可复制 GET API 链接
                    const base = window.location.origin;
                    const usp = new URLSearchParams();
                    usp.set('stock_code', code);
                    usp.set('dividend_type', dividend.value);
                    usp.set('include_realtime', 'true');
                    usp.set('preview_limit', '5');
                    if(mode.value === 'kline'){
                        usp.set('periods', period.value);
                    }else{
                        // 实时模式：不传K线参数，改为显式 only_realtime=true
                        usp.set('only_realtime', 'true');
                    }
                    const fullUrl = `${base}/api/instant_query?${usp.toString()}`;
                    apiUrlEl.value = fullUrl;
                    apiOpen.href = fullUrl;
                    apiBox.style.display = '';
                }catch(e){ resultEl.textContent = '请求异常: ' + e; }
                finally{ btn.disabled = false; }
            });
            apiCopy?.addEventListener('click', async ()=>{
                try{ await navigator.clipboard.writeText(apiUrlEl.value); apiCopy.textContent='已复制'; setTimeout(()=>apiCopy.textContent='复制链接', 1200); }catch(e){}
            });
        })();
        </script>
        </div>
    </body>
    </html>
    '''
    
    # 计算统计信息
    total_files = len(files)
    json_files = len([f for f in files if f['type'] == 'JSON'])
    csv_files = len([f for f in files if f['type'] == 'CSV'])
    total_size_mb = round(sum(f['size_mb'] for f in files), 2)
    
    # 为每个文件添加解析信息
    for file in files:
        file['info'] = parse_filename(file['name'])
    
    from jinja2 import Template
    template_obj = Template(template)
    return template_obj.render(
        files=files,
        total_files=total_files,
        json_files=json_files,
        csv_files=csv_files,
        total_size_mb=total_size_mb
    )

@app.route('/api/files')
@require_auth
def list_files():
    """API: 获取所有文件列表"""
    files = get_data_files()
    for file in files:
        file['info'] = parse_filename(file['name'])
    
    return jsonify({
        'success': True,
        'count': len(files),
        'files': files
    })

@app.route('/api/files/<filename>')
@require_auth
def get_file(filename):
    """API: 获取特定文件内容"""
    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': f'文件 {filename} 不存在'}), 404
    
    if not filename.lower().endswith(('.json', '.csv')):
        return jsonify({'error': '只支持JSON和CSV文件'}), 400
    
    format_type = request.args.get('format', 'original').lower()
    limit = request.args.get('limit', type=int)  # 获取limit参数
    encoding = request.args.get('encoding', 'utf-8').lower()  # 获取编码参数，默认utf-8
    reverse_time = request.args.get('reverse_time', 'false').lower() in ['true', '1', 'yes']  # 是否逆转时间排序
    
    try:
        if filename.lower().endswith('.json'):
            with open(filepath, 'r', encoding=encoding) as f:
                data = json.load(f)
            
            # 如果数据是列表且指定了limit，只返回最后N条
            if limit and isinstance(data, list):
                original_length = len(data)
                data = data[-limit:] if limit < len(data) else data
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'total_rows': original_length,
                    'returned_rows': len(data),
                    'limit_applied': limit,
                    'data': data
                })
            
            if format_type == 'json' or format_type == 'original':
                return jsonify(data)
        
        elif filename.lower().endswith('.csv'):
            if format_type == 'json':
                # CSV转换为JSON格式
                df = pd.read_csv(filepath, encoding=encoding)
                total_rows = len(df)
                
                # 如果需要逆转时间排序，寻找时间字段并排序
                if reverse_time:
                    # 常见的时间字段名称
                    time_columns = ['datetime', 'time', 'date', 'timestamp', 'create_time', 'update_time']
                    time_column = None
                    
                    # 查找存在的时间字段
                    for col in time_columns:
                        if col in df.columns:
                            time_column = col
                            break
                    
                    if time_column:
                        # 如果是字符串格式的日期时间，尝试转换为datetime类型进行排序
                        if df[time_column].dtype == 'object':
                            try:
                                df[time_column] = pd.to_datetime(df[time_column])
                            except:
                                pass  # 如果转换失败，保持原始格式
                        
                        # 按时间字段降序排序（最新的在前面）
                        df = df.sort_values(by=time_column, ascending=False)
                
                # 如果指定了limit，在排序后取前N条记录
                if limit and limit < total_rows:
                    df = df.head(limit) if reverse_time else df.tail(limit)
                
                # 如果之前转换了时间格式，转换回字符串以便JSON序列化
                for col in df.columns:
                    if df[col].dtype == 'datetime64[ns]':
                        df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                data = df.to_dict('records')
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'total_rows': total_rows,
                    'returned_rows': len(data),
                    'limit_applied': limit if limit else None,
                    'reverse_time_applied': reverse_time,
                    'columns': list(df.columns),
                    'data': data
                })
            else:
                # 返回原始CSV内容（不支持limit）
                if limit:
                    return jsonify({'error': '原始CSV格式不支持limit参数，请使用format=json'}), 400
                
                # 如果指定了非UTF-8编码，需要转换编码
                if encoding != 'utf-8':
                    with open(filepath, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    from flask import Response
                    return Response(content, mimetype='text/csv; charset=utf-8')
                else:
                    return send_file(filepath, as_attachment=False, mimetype='text/csv')
    
    except Exception as e:
        logger.error(f"读取文件 {filename} 时出错: {str(e)}")
        return jsonify({'error': f'读取文件时出错: {str(e)}'}), 500

@app.route('/api/download/<filename>')
@require_auth
def download_file(filename):
    """API: 下载文件"""
    filepath = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': f'文件 {filename} 不存在'}), 404
    
    if not filename.lower().endswith(('.json', '.csv')):
        return jsonify({'error': '只支持JSON和CSV文件'}), 400
    
    return send_file(filepath, as_attachment=True)

@app.route('/api/stats')
@require_auth
def get_stats():
    """API: 获取统计信息"""
    files = get_data_files()
    
    stats = {
        'total_files': len(files),
        'json_files': len([f for f in files if f['type'] == 'JSON']),
        'csv_files': len([f for f in files if f['type'] == 'CSV']),
        'total_size_bytes': sum(f['size'] for f in files),
        'total_size_mb': round(sum(f['size_mb'] for f in files), 2),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """登出功能"""
    session.pop('authenticated', None)
    return jsonify({'success': True, 'message': '已成功登出'})

# ========================= MCP (Model Context Protocol) 接口 ========================= #

# MCP 协议版本
MCP_PROTOCOL_VERSION = "2024-11-05"

# MCP 服务器信息
MCP_SERVER_INFO = {
    "name": "qmt-stock-server",
    "version": "1.0.0"
}

# 定义 MCP 可用工具
MCP_TOOLS = [
    {
        "name": "list_files",
        "description": "列出所有可用的股票数据文件（JSON和CSV格式）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_file",
        "description": "获取指定股票数据文件的内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "文件名，如 600689_SH_kline_1d.csv"
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "original"],
                    "description": "返回格式，默认为json"
                },
                "limit": {
                    "type": "integer",
                    "description": "限制返回记录数"
                },
                "reverse_time": {
                    "type": "boolean",
                    "description": "是否按时间倒序排列（最新在前）"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "get_stats",
        "description": "获取服务器统计信息，包括文件数量、总大小等",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "instant_query",
        "description": "即时查询股票数据，拉取最新K线和实时价格",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stock_code": {
                    "type": "string",
                    "description": "股票代码，如 600689.SH"
                },
                "dividend_type": {
                    "type": "string",
                    "enum": ["front", "none", "back"],
                    "description": "复权类型：front(前复权)、none(不复权)、back(后复权)"
                },
                "periods": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "K线周期列表，如 ['1d', '1w']，留空则只获取实时价格"
                },
                "include_realtime": {
                    "type": "boolean",
                    "description": "是否包含实时价格数据"
                }
            },
            "required": ["stock_code"]
        }
    }
]

def mcp_error_response(req_id, code, message):
    """构造 MCP 错误响应"""
    return jsonify({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": message
        }
    })

def mcp_success_response(req_id, result):
    """构造 MCP 成功响应"""
    return jsonify({
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result
    })

def handle_mcp_initialize(req_id, params):
    """处理 MCP initialize 请求"""
    return mcp_success_response(req_id, {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            "tools": {},
            "resources": {}
        },
        "serverInfo": MCP_SERVER_INFO
    })

def handle_mcp_tools_list(req_id, params):
    """处理 MCP tools/list 请求"""
    return mcp_success_response(req_id, {
        "tools": MCP_TOOLS
    })

def handle_mcp_tools_call(req_id, params):
    """处理 MCP tools/call 请求"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    try:
        if tool_name == "list_files":
            files = get_data_files()
            for file in files:
                file['info'] = parse_filename(file['name'])
            return mcp_success_response(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": True,
                        "count": len(files),
                        "files": files
                    }, ensure_ascii=False, indent=2)
                }]
            })
        
        elif tool_name == "get_file":
            filename = arguments.get("filename")
            if not filename:
                return mcp_error_response(req_id, -32602, "缺少参数: filename")
            
            filepath = os.path.join(BASE_DIR, filename)
            if not os.path.exists(filepath):
                return mcp_error_response(req_id, -32602, f"文件 {filename} 不存在")
            
            format_type = arguments.get("format", "json")
            limit = arguments.get("limit")
            reverse_time = arguments.get("reverse_time", False)
            
            if filename.lower().endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if limit and isinstance(data, list):
                    data = data[-limit:]
            elif filename.lower().endswith('.csv'):
                df = pd.read_csv(filepath, encoding='utf-8')
                if reverse_time:
                    time_columns = ['datetime', 'time', 'date', 'timestamp']
                    for col in time_columns:
                        if col in df.columns:
                            df = df.sort_values(by=col, ascending=False)
                            break
                if limit:
                    df = df.head(limit) if reverse_time else df.tail(limit)
                data = df.to_dict('records')
            else:
                return mcp_error_response(req_id, -32602, "不支持的文件类型")
            
            return mcp_success_response(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": True,
                        "filename": filename,
                        "data": data
                    }, ensure_ascii=False, indent=2)
                }]
            })
        
        elif tool_name == "get_stats":
            files = get_data_files()
            stats = {
                'total_files': len(files),
                'json_files': len([f for f in files if f['type'] == 'JSON']),
                'csv_files': len([f for f in files if f['type'] == 'CSV']),
                'total_size_bytes': sum(f['size'] for f in files),
                'total_size_mb': round(sum(f['size_mb'] for f in files), 2),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            return mcp_success_response(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": True,
                        "stats": stats
                    }, ensure_ascii=False, indent=2)
                }]
            })
        
        elif tool_name == "instant_query":
            if perform_instant_update is None:
                return mcp_error_response(req_id, -32603, "即时查询模块未加载")
            
            stock_code = arguments.get("stock_code")
            if not stock_code:
                return mcp_error_response(req_id, -32602, "缺少参数: stock_code")
            
            dividend_type = arguments.get("dividend_type", "front")
            periods = arguments.get("periods")
            include_realtime = arguments.get("include_realtime", True)
            
            result = perform_instant_update(
                stock_code=stock_code,
                dividend_type=dividend_type,
                include_periods=periods,
                include_realtime=include_realtime,
                preview_limit=5
            )
            
            return mcp_success_response(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }]
            })
        
        else:
            return mcp_error_response(req_id, -32601, f"未知的工具: {tool_name}")
    
    except Exception as e:
        logger.error(f"MCP tools/call 错误: {e}")
        return mcp_error_response(req_id, -32603, f"工具调用失败: {str(e)}")

def handle_mcp_resources_list(req_id, params):
    """处理 MCP resources/list 请求"""
    files = get_data_files()
    resources = []
    for file in files:
        resources.append({
            "uri": f"file:///{file['name']}",
            "name": file['name'],
            "description": f"{file['type']}格式股票数据文件，大小{file['size_mb']}MB",
            "mimeType": "application/json" if file['type'] == 'JSON' else "text/csv"
        })
    return mcp_success_response(req_id, {
        "resources": resources
    })

def handle_mcp_resources_read(req_id, params):
    """处理 MCP resources/read 请求"""
    uri = params.get("uri", "")
    # 从 uri 提取文件名
    filename = uri.replace("file:///", "")
    
    if not filename:
        return mcp_error_response(req_id, -32602, "缺少参数: uri")
    
    filepath = os.path.join(BASE_DIR, filename)
    if not os.path.exists(filepath):
        return mcp_error_response(req_id, -32602, f"资源 {filename} 不存在")
    
    try:
        if filename.lower().endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            mime_type = "application/json"
        elif filename.lower().endswith('.csv'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            mime_type = "text/csv"
        else:
            return mcp_error_response(req_id, -32602, "不支持的文件类型")
        
        return mcp_success_response(req_id, {
            "contents": [{
                "uri": uri,
                "mimeType": mime_type,
                "text": content
            }]
        })
    except Exception as e:
        return mcp_error_response(req_id, -32603, f"读取资源失败: {str(e)}")

@app.route('/mcp', methods=['POST'])
@require_auth
def mcp_endpoint():
    """
    MCP (Model Context Protocol) JSON-RPC 2.0 端点
    
    支持的方法:
    - initialize: 初始化 MCP 连接
    - tools/list: 列出可用工具
    - tools/call: 调用工具
    - resources/list: 列出可用资源
    - resources/read: 读取资源内容
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return mcp_error_response(None, -32700, "无效的JSON")
        
        # 验证 JSON-RPC 格式
        if data.get("jsonrpc") != "2.0":
            return mcp_error_response(data.get("id"), -32600, "无效的 JSON-RPC 版本")
        
        method = data.get("method")
        req_id = data.get("id")
        params = data.get("params", {})
        
        if not method:
            return mcp_error_response(req_id, -32600, "缺少 method 字段")
        
        # 路由到对应的处理函数
        handlers = {
            "initialize": handle_mcp_initialize,
            "tools/list": handle_mcp_tools_list,
            "tools/call": handle_mcp_tools_call,
            "resources/list": handle_mcp_resources_list,
            "resources/read": handle_mcp_resources_read,
        }
        
        handler = handlers.get(method)
        if handler:
            return handler(req_id, params)
        else:
            return mcp_error_response(req_id, -32601, f"未知的方法: {method}")
    
    except Exception as e:
        logger.error(f"MCP 端点错误: {e}")
        return mcp_error_response(None, -32603, f"内部错误: {str(e)}")

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '页面不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

# ========================= 新增：即时查询 API 与页面 ========================= #

@app.route('/api/instant_query', methods=['GET', 'POST'])
@require_auth
def api_instant_query():
    """即时查询：按股票代码触发一次 K线+实时价格 更新并返回结果。"""
    if perform_instant_update is None:
        return jsonify({'error': '即时查询模块未加载'}), 500

    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            stock_code = payload.get('stock_code') or request.form.get('stock_code')
            dividend_type = payload.get('dividend_type', 'front')
            include_realtime = payload.get('include_realtime', True)
            preview_limit = int(payload.get('preview_limit', 5))
            periods = payload.get('periods')
            # 支持仅实时的显式参数
            only_realtime = payload.get('only_realtime') or request.form.get('only_realtime')
            mode = payload.get('mode') or request.form.get('mode')
        else:
            stock_code = request.args.get('stock_code')
            dividend_type = request.args.get('dividend_type', 'front')
            include_realtime = request.args.get('include_realtime', 'true').lower() in ['true', '1', 'yes']
            preview_limit = request.args.get('preview_limit', default=5, type=int)
            periods_arg = request.args.get('periods')
            periods = [p.strip() for p in periods_arg.split(',')] if periods_arg else None
            # 支持仅实时的显式参数
            only_realtime = request.args.get('only_realtime', 'false').lower() in ['true', '1', 'yes']
            mode = request.args.get('mode')

        if not stock_code:
            return jsonify({'error': '缺少参数 stock_code'}), 400

        # 如果显式声明仅实时或模式为realtime，则强制不拉取任何K线
        if only_realtime or (isinstance(mode, str) and mode.lower() == 'realtime'):
            periods = []

        # 调用即时更新
        out = perform_instant_update(
            stock_code=stock_code,
            dividend_type=dividend_type,
            include_periods=periods,
            include_realtime=include_realtime,
            preview_limit=preview_limit,
        )

        status_code = 200 if out.get('success') else 500
        return jsonify(out), status_code

    except Exception as e:
        logger.error(f"即时查询接口错误: {e}")
        return jsonify({'error': f'即时查询失败: {str(e)}'}), 500


@app.route('/instant', methods=['GET'])
@require_auth
def instant_page():
    """即时查询的简易页面，提供股票代码输入并显示结果。"""
    page = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>即时查询 - 股票数据服务器</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 20px; }
            .form-row { display: flex; gap: 10px; margin-bottom: 15px; }
            input, select, button { padding: 10px; font-size: 14px; }
            input[type=text] { flex: 1; border: 2px solid #e1e5e9; border-radius: 6px; }
            select { border: 2px solid #e1e5e9; border-radius: 6px; }
            button { background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; }
            button:disabled { background: #a3b0f0; cursor: not-allowed; }
            .result { margin-top: 20px; white-space: pre-wrap; background: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e1e5e9; font-family: monospace; font-size: 13px; }
            .api-link { margin-top: 10px; padding: 10px; background: #fffbe6; border: 1px solid #ffe58f; border-radius: 6px; font-size: 12px; }
            .api-link .url { width: 100%; box-sizing: border-box; margin-top: 6px; padding: 8px; font-family: monospace; font-size: 12px; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }
            .api-actions { margin-top: 6px; }
            .small { color: #666; font-size: 12px; }
            .files { margin-top: 10px; }
            .files a { display: inline-block; margin-right: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ 即时查询</h1>
            <div class="form-row">
                <input id="stock" type="text" placeholder="请输入股票代码，如 600689.SH" />
                <select id="dividend">
                    <option value="front" selected>前复权</option>
                    <option value="none">不复权</option>
                    <option value="back">后复权</option>
                </select>
                <button id="btn">查询</button>
            </div>
            <div class="small">提示：该操作会即时拉取K线与最新价格，并保存到 ./data 目录，可能耗时数秒。</div>
            <div class="files" id="files"></div>
            <div class="result" id="result"></div>
            <div class="api-link" id="apiBox" style="display:none;">
                <div><strong>可复制API(GET)：</strong><span class="small">（直接在程序中请求该地址获取同样数据）</span></div>
                <input class="url" id="apiUrl" readonly value="" />
                <div class="api-actions">
                    <button id="copyBtn">复制链接</button>
                    <a id="openLink" href="#" target="_blank" style="margin-left:10px;">新窗口打开</a>
                </div>
            </div>
        </div>

        <script>
            const btn = document.getElementById('btn');
            const stock = document.getElementById('stock');
            const dividend = document.getElementById('dividend');
            const resultEl = document.getElementById('result');
            const filesEl = document.getElementById('files');
            const apiBox = document.getElementById('apiBox');
            const apiUrlEl = document.getElementById('apiUrl');
            const openLink = document.getElementById('openLink');
            const copyBtn = document.getElementById('copyBtn');

            btn.addEventListener('click', async () => {
                const code = stock.value.trim();
                if (!code) { alert('请输入股票代码'); return; }
                btn.disabled = true; resultEl.textContent = '正在查询，请稍候...'; filesEl.innerHTML = '';
                try {
                    const resp = await fetch('/api/instant_query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ stock_code: code, dividend_type: dividend.value, include_realtime: true })
                    });
                    const data = await resp.json();
                    if (!resp.ok || !data.success) {
                        resultEl.textContent = '查询失败: ' + (data.message || data.error || '未知错误');
                        apiBox.style.display = 'none';
                        return;
                    }

                    // 文件链接
                    const kfiles = data.kline_files || {}; 
                    const links = [];
                    for (const [period, fname] of Object.entries(kfiles)) {
                        const url = `/api/files/${fname}?format=json&reverse_time=true&limit=50`;
                        links.push(`<a href="${url}" target="_blank">${period} 最近50条</a>`);
                    }
                    filesEl.innerHTML = links.join(' | ');

                    // 构造显示结果（实时 + 简要预览）
                    const show = {
                        stock_code: data.stock_code,
                        realtime: data.realtime_data,
                        previews: data.kline_preview
                    };
                    resultEl.textContent = JSON.stringify(show, null, 2);

                    // 构造可复制API(GET)链接
                    const base = window.location.origin;
                    const params = new URLSearchParams();
                    params.set('stock_code', code);
                    params.set('dividend_type', dividend.value);
                    params.set('include_realtime', 'true');
                    params.set('preview_limit', '5');
                    const fullUrl = `${base}/api/instant_query?${params.toString()}`;
                    apiUrlEl.value = fullUrl;
                    openLink.href = fullUrl;
                    apiBox.style.display = '';
                } catch (e) {
                    resultEl.textContent = '请求异常: ' + e;
                    apiBox.style.display = 'none';
                } finally {
                    btn.disabled = false;
                }
            });

            copyBtn?.addEventListener('click', async () => {
                try { await navigator.clipboard.writeText(apiUrlEl.value); copyBtn.textContent = '已复制'; setTimeout(()=>copyBtn.textContent='复制链接', 1200); } catch(e) {}
            });
        </script>
    </body>
    </html>
    '''
    from jinja2 import Template
    return Template(page).render()

if __name__ == '__main__':
    args = parse_args()
    API_KEY = args.api_key
    
    print("🚀 启动股票数据Web服务器...")
    print(f"📡 服务地址: http://{args.host}:{args.port}")
    print(f"📊 API文档: http://{args.host}:{args.port}")
    
    if API_KEY:
        print(f"🔐 认证模式: 已启用 (API密钥: {API_KEY[:8]}...)")
        print("🔑 认证方式:")
        print("   - Bearer Token: Authorization: Bearer <your-api-key>")
        print("   - Query参数: ?api_key=<your-api-key>")
        print("   - Web登录: 浏览器访问进行登录")
    else:
        print("⚠️  认证模式: 未启用 (公开访问)")
    
    print("=" * 50)
    
    # 显示可用文件
    files = get_data_files()
    print(f"📁 发现 {len(files)} 个数据文件:")
    for file in files[:5]:  # 只显示前5个
        print(f"   - {file['name']} ({file['size_mb']} MB)")
    if len(files) > 5:
        print(f"   ... 还有 {len(files) - 5} 个文件")
    
    print("=" * 50)
    
    # 启动服务器
    app.run(host=args.host, port=args.port, debug=args.debug)
