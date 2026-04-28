/**
 * Docker Port Manager - 前端 JavaScript
 */

// ============ 全局状态 ============
let currentPage = 'dashboard';
let presets = {};

// ============ API 请求封装 ============
async function api(method, path, data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) options.body = JSON.stringify(data);

    try {
        const res = await fetch(`/api${path}`, options);
        const json = await res.json();
        if (!json.success && json.error) {
            throw new Error(json.error);
        }
        return json;
    } catch (e) {
        if (e.message.includes('Failed to fetch')) {
            throw new Error('无法连接到服务器，请检查服务是否运行');
        }
        throw e;
    }
}

// ============ Toast 通知 ============
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============ 页面切换 ============
function switchPage(page) {
    currentPage = page;

    // 更新导航高亮
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // 切换页面显示
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add('active');

    // 更新标题
    const titles = {
        dashboard: '仪表盘',
        rules: '转发规则',
        ports: '端口状态',
        network: '网络工具',
        containers: '容器列表',
    };
    document.getElementById('pageTitle').textContent = titles[page] || page;

    // 加载数据
    refreshCurrentPage();
}

function refreshCurrentPage() {
    switch (currentPage) {
        case 'dashboard': loadDashboard(); break;
        case 'rules': loadRules(); break;
        case 'ports': loadPorts(); break;
        case 'containers': loadContainers(); break;
    }
}

// ============ 侧边栏 ============
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ============ 仪表盘 ============
async function loadDashboard() {
    try {
        const [systemRes, rulesRes, portsRes] = await Promise.all([
            api('GET', '/system/info'),
            api('GET', '/rules'),
            api('GET', '/ports'),
        ]);

        // 更新统计
        const dockerInfo = systemRes.data.docker;
        document.getElementById('statContainers').textContent = dockerInfo.containers_running || 0;
        document.getElementById('statRules').textContent = rulesRes.data.length;
        document.getElementById('statPorts').textContent = portsRes.data.total_used_ports;
        document.getElementById('statVersion').textContent = dockerInfo.version || '-';

        // 更新系统状态
        const statusEl = document.getElementById('systemStatus');
        statusEl.querySelector('.status-dot').classList.remove('error');
        statusEl.querySelector('.status-text').textContent = 'Docker 已连接';

        // 转发规则列表
        const rulesHtml = rulesRes.data.length === 0
            ? '<p class="empty-text">暂无转发规则，点击右上角创建</p>'
            : rulesRes.data.map(rule => `
                <div class="rule-item">
                    <div class="rule-info">
                        <span class="rule-name">${escapeHtml(rule.name)}</span>
                        <span class="rule-detail">
                            :${rule.listen_port} → ${escapeHtml(rule.target)}
                            ${rule.description ? ' | ' + escapeHtml(rule.description) : ''}
                        </span>
                    </div>
                    <span class="badge ${rule.state === 'running' ? 'badge-success' : 'badge-danger'}">
                        ${rule.state === 'running' ? '运行中' : '已停止'}
                    </span>
                </div>
            `).join('');
        document.getElementById('dashboardRules').innerHTML = rulesHtml;

        // 端口概览
        const ports = portsRes.data.used_ports.slice(0, 15);
        const portsHtml = ports.length === 0
            ? '<p class="empty-text">暂无端口使用</p>'
            : ports.map(p => `
                <div class="port-item">
                    <span class="port-number">:${p.host_port}</span>
                    <span class="port-detail">${escapeHtml(p.container_name)} (${escapeHtml(p.container_port)})</span>
                </div>
            `).join('');
        document.getElementById('dashboardPorts').innerHTML = portsHtml;

    } catch (e) {
        showToast(e.message, 'error');
        const statusEl = document.getElementById('systemStatus');
        statusEl.querySelector('.status-dot').classList.add('error');
        statusEl.querySelector('.status-text').textContent = '连接失败';
    }
}

// ============ 转发规则 ============
async function loadRules() {
    try {
        const res = await api('GET', '/rules');
        const tbody = document.getElementById('rulesBody');

        if (res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-text">暂无转发规则</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(rule => `
            <tr>
                <td><strong>${escapeHtml(rule.name)}</strong></td>
                <td><code>:${rule.listen_port}</code></td>
                <td><code>${escapeHtml(rule.target)}</code></td>
                <td><span class="badge badge-info">${rule.protocol.toUpperCase()}</span></td>
                <td>
                    <span class="badge ${rule.state === 'running' ? 'badge-success' : 'badge-danger'}">
                        ${rule.state === 'running' ? '运行中' : '已停止'}
                    </span>
                </td>
                <td class="text-muted">${escapeHtml(rule.description || '-')}</td>
                <td>
                    <div class="action-group">
                        ${rule.state === 'running'
                            ? `<button class="btn btn-xs btn-warning" onclick="stopRule('${escapeHtml(rule.name)}')">停止</button>`
                            : `<button class="btn btn-xs btn-success" onclick="startRule('${escapeHtml(rule.name)}')">启动</button>`
                        }
                        <button class="btn btn-xs btn-secondary" onclick="showLogs('${escapeHtml(rule.name)}')">日志</button>
                        <button class="btn btn-xs btn-danger" onclick="deleteRule('${escapeHtml(rule.name)}')">删除</button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function createRule() {
    const name = document.getElementById('ruleName').value.trim();
    const listenPort = parseInt(document.getElementById('listenPort').value);
    const targetHost = document.getElementById('targetHost').value.trim();
    const targetPort = parseInt(document.getElementById('targetPort').value);
    const protocol = document.getElementById('ruleProtocol').value;
    const description = document.getElementById('ruleDescription').value.trim();
    const preset = document.getElementById('presetSelect').value;

    if (!name || !listenPort || !targetHost || !targetPort) {
        showToast('请填写所有必填项', 'warning');
        return;
    }

    const btn = document.getElementById('createRuleBtn');
    btn.disabled = true;
    btn.textContent = '创建中...';

    try {
        await api('POST', '/rules', {
            name, listen_port: listenPort, target_host: targetHost,
            target_port: targetPort, protocol, description, preset,
        });
        showToast('转发规则创建成功', 'success');
        closeCreateRuleModal();
        refreshCurrentPage();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '创建规则';
    }
}

async function deleteRule(name) {
    if (!confirm(`确定要删除转发规则 "${name}" 吗？`)) return;
    try {
        await api('DELETE', `/rules/${name}`);
        showToast(`规则 "${name}" 已删除`, 'success');
        refreshCurrentPage();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function startRule(name) {
    try {
        await api('POST', `/rules/${name}/start`);
        showToast(`规则 "${name}" 已启动`, 'success');
        refreshCurrentPage();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function stopRule(name) {
    try {
        await api('POST', `/rules/${name}/stop`);
        showToast(`规则 "${name}" 已停止`, 'warning');
        refreshCurrentPage();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function showLogs(name) {
    document.getElementById('logModalTitle').textContent = `日志 - ${name}`;
    document.getElementById('logContent').textContent = '加载中...';
    document.getElementById('logModal').classList.add('active');

    try {
        const res = await api('GET', `/rules/${name}/logs?tail=200`);
        document.getElementById('logContent').textContent = res.data || '暂无日志';
    } catch (e) {
        document.getElementById('logContent').textContent = `加载失败: ${e.message}`;
    }
}

function closeLogModal() {
    document.getElementById('logModal').classList.remove('active');
}

// ============ 端口状态 ============
async function loadPorts() {
    try {
        const res = await api('GET', '/ports');
        const tbody = document.getElementById('portsBody');
        const ports = res.data.used_ports;

        if (ports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-text">暂无端口使用</td></tr>';
            return;
        }

        const forwardPorts = new Set(res.data.forward_ports.map(p => p.port));

        tbody.innerHTML = ports.map(p => `
            <tr>
                <td><code>:${p.host_port}</code></td>
                <td>${escapeHtml(p.container_port)}</td>
                <td>
                    ${escapeHtml(p.container_name)}
                    ${forwardPorts.has(p.host_port) ? '<span class="badge badge-dpm" style="margin-left:4px">DPM</span>' : ''}
                </td>
                <td>${escapeHtml(p.host_ip)}</td>
                <td>${forwardPorts.has(p.host_port) ? '<span class="badge badge-info">转发</span>' : '<span class="badge badge-warning">其他</span>'}</td>
            </tr>
        `).join('');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function checkSpecificPort() {
    const port = parseInt(document.getElementById('checkPortInput').value);
    if (!port || port < 1 || port > 65535) {
        showToast('请输入有效端口号 (1-65535)', 'warning');
        return;
    }

    try {
        const res = await api('GET', `/ports/check/${port}`);
        if (res.data.available) {
            showToast(`端口 ${port} 可用`, 'success');
        } else {
            showToast(`端口 ${port} 已被容器 "${res.data.conflict.container_name}" 占用`, 'error');
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ============ 网络工具 ============
async function runPing() {
    const host = document.getElementById('pingHost').value.trim();
    const count = parseInt(document.getElementById('pingCount').value) || 4;

    if (!host) {
        showToast('请输入目标地址', 'warning');
        return;
    }

    const btn = document.getElementById('pingBtn');
    btn.disabled = true;
    btn.textContent = 'Ping 中...';
    document.getElementById('pingOutput').textContent = '正在执行...';

    try {
        const res = await api('POST', '/network/ping', { host, count });
        const data = res.data;
        let output = '';
        if (data.success) {
            output = `--- ${data.host} ping 统计 ---\n`;
            output += `${data.packets_sent} 个包发送, ${data.packets_received} 个包接收, ${data.packet_loss}% 丢包\n`;
            output += `平均延迟: ${data.avg_time_ms} ms\n\n`;
        } else {
            output = `Ping 失败: ${data.error}\n\n`;
        }
        output += data.output || '';
        document.getElementById('pingOutput').textContent = output;
    } catch (e) {
        document.getElementById('pingOutput').textContent = `错误: ${e.message}`;
    } finally {
        btn.disabled = false;
        btn.textContent = '开始 Ping';
    }
}

async function runPortTest() {
    const host = document.getElementById('portTestHost').value.trim();
    const port = parseInt(document.getElementById('portTestPort').value);

    if (!host || !port) {
        showToast('请输入目标地址和端口号', 'warning');
        return;
    }

    const btn = document.getElementById('portTestBtn');
    btn.disabled = true;
    btn.textContent = '测试中...';

    try {
        const res = await api('POST', '/network/port-test', { host, port });
        const data = res.data;
        const outputEl = document.getElementById('portTestOutput');

        if (data.open) {
            outputEl.innerHTML = `
                <div style="color: var(--success); font-weight: 600; margin-bottom: 8px;">
                    ✓ 端口 ${port} 开放
                </div>
                <div>目标: ${escapeHtml(host)}:${port}</div>
                <div>响应时间: ${data.response_time_ms} ms</div>
            `;
        } else {
            outputEl.innerHTML = `
                <div style="color: var(--danger); font-weight: 600; margin-bottom: 8px;">
                    ✗ 端口 ${port} 未开放
                </div>
                <div>目标: ${escapeHtml(host)}:${port}</div>
                <div>错误: ${escapeHtml(data.error || '未知')}</div>
            `;
        }
    } catch (e) {
        document.getElementById('portTestOutput').innerHTML = `<span style="color:var(--danger)">错误: ${escapeHtml(e.message)}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '测试端口';
    }
}

async function runDnsResolve() {
    const host = document.getElementById('dnsHost').value.trim();

    if (!host) {
        showToast('请输入域名', 'warning');
        return;
    }

    const btn = document.getElementById('dnsBtn');
    btn.disabled = true;
    btn.textContent = '解析中...';

    try {
        const res = await api('POST', '/network/dns', { host });
        const data = res.data;
        const outputEl = document.getElementById('dnsOutput');

        if (data.success) {
            outputEl.innerHTML = `
                <div style="color: var(--success); font-weight: 600; margin-bottom: 8px;">
                    ✓ 解析成功
                </div>
                <div>域名: ${escapeHtml(host)}</div>
                <div>IP 地址: <code>${escapeHtml(data.ip)}</code></div>
            `;
        } else {
            outputEl.innerHTML = `
                <div style="color: var(--danger); font-weight: 600; margin-bottom: 8px;">
                    ✗ 解析失败
                </div>
                <div>错误: ${escapeHtml(data.error || '未知')}</div>
            `;
        }
    } catch (e) {
        document.getElementById('dnsOutput').innerHTML = `<span style="color:var(--danger)">错误: ${escapeHtml(e.message)}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '解析';
    }
}

// ============ 容器列表 ============
async function loadContainers() {
    const showAll = document.getElementById('showAllContainers').checked;
    try {
        const res = await api('GET', `/containers?all=${showAll}`);
        const tbody = document.getElementById('containersBody');

        if (res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-text">暂无容器</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(c => {
            const portsStr = c.ports.length > 0
                ? c.ports.map(p => `${p.host_ip === '0.0.0.0' ? '*' : p.host_ip}:${p.host_port}→${p.container_port}`).join(', ')
                : '-';
            const isDpm = c.labels && c.labels['dpm.managed'] === 'true';

            return `
                <tr>
                    <td>
                        ${escapeHtml(c.name)}
                        ${isDpm ? '<span class="badge badge-dpm" style="margin-left:4px">DPM</span>' : ''}
                    </td>
                    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${escapeHtml(c.image)}</td>
                    <td>
                        <span class="badge ${c.state === 'running' ? 'badge-success' : 'badge-danger'}">
                            ${c.status}
                        </span>
                    </td>
                    <td><code style="font-size:11px">${escapeHtml(portsStr)}</code></td>
                    <td><code>${c.id}</code></td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// ============ 新建规则弹窗 ============
function showCreateRuleModal() {
    document.getElementById('createRuleModal').classList.add('active');
    // 重置表单
    document.getElementById('presetSelect').value = '';
    document.getElementById('ruleName').value = '';
    document.getElementById('listenPort').value = '';
    document.getElementById('targetHost').value = '';
    document.getElementById('targetPort').value = '';
    document.getElementById('ruleProtocol').value = 'tcp';
    document.getElementById('ruleDescription').value = '';
    document.getElementById('portCheckResult').className = 'port-check-result';
    document.getElementById('portCheckResult').textContent = '';
}

function closeCreateRuleModal() {
    document.getElementById('createRuleModal').classList.remove('active');
}

async function applyPreset() {
    const presetKey = document.getElementById('presetSelect').value;
    if (!presetKey) return;

    try {
        const res = await api('GET', '/presets');
        const preset = res.data[presetKey];
        if (preset) {
            document.getElementById('listenPort').value = preset.port;
            document.getElementById('targetPort').value = preset.port;
            document.getElementById('ruleDescription').value = preset.description;

            // 自动生成规则名
            const nameInput = document.getElementById('ruleName');
            if (!nameInput.value.trim()) {
                nameInput.value = `${presetKey}-forward`;
            }
        }
    } catch (e) {
        showToast('加载预设失败', 'error');
    }
}

// 监听端口输入变化，实时检查
document.getElementById('listenPort').addEventListener('change', async function() {
    const port = parseInt(this.value);
    const resultEl = document.getElementById('portCheckResult');

    if (!port || port < 1 || port > 65535) {
        resultEl.className = 'port-check-result';
        return;
    }

    try {
        const res = await api('GET', `/ports/check/${port}`);
        if (res.data.available) {
            resultEl.className = 'port-check-result success';
            resultEl.textContent = `✓ 端口 ${port} 可用`;
        } else {
            resultEl.className = 'port-check-result error';
            resultEl.textContent = `✗ 端口 ${port} 已被容器 "${res.data.conflict.container_name}" 占用`;
        }
    } catch (e) {
        resultEl.className = 'port-check-result';
    }
});

// ============ 工具函数 ============
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});

// 点击弹窗外部关闭
document.getElementById('createRuleModal').addEventListener('click', function(e) {
    if (e.target === this) closeCreateRuleModal();
});

document.getElementById('logModal').addEventListener('click', function(e) {
    if (e.target === this) closeLogModal();
});
