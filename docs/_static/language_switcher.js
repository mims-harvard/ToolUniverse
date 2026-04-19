// Language Switcher for ToolUniverse Documentation
(function() {
    'use strict';
    
    function isLocalhost() {
        const hostname = window.location.hostname;
        return hostname === 'localhost' || hostname === '127.0.0.1';
    }

    // 计算部署的基础前缀（例如 GitHub Pages 项目页面的 /<repo>/ 前缀）
    function getBasePrefix(pathname) {
        // Local development usually serves docs from the web root.
        if (isLocalhost()) {
            if (pathname.includes('/en/')) return pathname.split('/en/')[0] + '/';
            if (pathname.includes('/zh-CN/')) return pathname.split('/zh-CN/')[0] + '/';
            if (pathname.includes('/zh_CN/')) return pathname.split('/zh_CN/')[0] + '/';
            return '/';
        }

        // Always prefer explicit project base if present
        if (pathname.includes('/ToolUniverse/')) return '/ToolUniverse/';
        if (pathname.includes('/en/')) return pathname.split('/en/')[0] + '/';
        if (pathname.includes('/zh-CN/')) return pathname.split('/zh-CN/')[0] + '/';
        if (pathname.includes('/zh_CN/')) return pathname.split('/zh_CN/')[0] + '/';
        // Fallback: assume project page lives under /ToolUniverse/
        return '/ToolUniverse/';
    }

    // 检测当前语言
    function detectCurrentLanguage() {
        const path = window.location.pathname;
        if (path.includes('/zh-CN/') || path.includes('/zh_CN/')) {
            return 'zh_CN';
        }
        // 根路径或 /en/ 路径都视为英文
        return 'en';
    }
    
    // 切换语言
    function switchLanguage(newLang) {
        const currentPath = window.location.pathname;
        const origin = window.location.origin;
        const basePrefix = getBasePrefix(currentPath);

        function goIfExists(url, fallbackUrl) {
            fetch(url, { method: 'HEAD' })
                .then(function(response) {
                    if (response.ok) {
                        window.location.href = url;
                    } else if (fallbackUrl) {
                        window.location.href = fallbackUrl;
                    } else {
                        console.warn('Language target not found:', url);
                    }
                })
                .catch(function() {
                    if (fallbackUrl) {
                        window.location.href = fallbackUrl;
                    } else {
                        console.warn('Language target not reachable:', url);
                    }
                });
        }

        // 优先路径替换，保持当前位置文件一致
        if (currentPath.includes('/en/')) {
            if (newLang === 'zh_CN') {
                goIfExists(
                    origin + currentPath.replace('/en/', '/zh-CN/'),
                    origin + basePrefix + 'zh-CN/index.html'
                );
            }
            return;
        }
        if (currentPath.includes('/zh-CN/')) {
            if (newLang !== 'zh_CN') {
                goIfExists(
                    origin + currentPath.replace('/zh-CN/', '/en/'),
                    origin + basePrefix + 'en/index.html'
                );
            }
            return;
        }
        if (currentPath.includes('/zh_CN/')) {
            if (newLang !== 'zh_CN') {
                goIfExists(
                    origin + currentPath.replace('/zh_CN/', '/en/'),
                    origin + basePrefix + 'en/index.html'
                );
            }
            return;
        }

        // 兜底：当前不在语言目录下（例如根路径 / 或 /<repo>/index.html）
        // 解析当前文件名和路径
        let relativePath = '';
        if (currentPath !== '/' && currentPath !== basePrefix) {
            // 移除基础前缀，获取相对路径
            relativePath = currentPath.substring(basePrefix.length);
            // 确保路径以 / 开头
            if (!relativePath.startsWith('/')) {
                relativePath = '/' + relativePath;
            }
        } else {
            relativePath = '/index.html';
        }
        
        const targetLangPrefix = newLang === 'zh_CN' ? 'zh-CN' : 'en';
        const targetUrl = origin + basePrefix + targetLangPrefix + relativePath;
        const fallbackUrl = newLang === 'zh_CN'
            ? null
            : origin + basePrefix + 'index.html';
        goIfExists(targetUrl, fallbackUrl);
    }
    
    // 创建语言切换器
    function createLanguageSwitcher() {
        const currentLang = detectCurrentLanguage();
        
        const switcher = document.createElement('div');
        switcher.className = 'language-switcher';
        switcher.innerHTML = `
            <select id="lang-select" aria-label="Choose language">
                <option value="en" ${currentLang === 'en' ? 'selected' : ''}>🇬🇧 English</option>
                <option value="zh_CN" ${currentLang === 'zh_CN' ? 'selected' : ''}>🇨🇳 简体中文</option>
            </select>
        `;
        
        document.body.appendChild(switcher);
        
        // 添加事件监听
        const select = document.getElementById('lang-select');
        select.addEventListener('change', function() {
            switchLanguage(this.value);
        });
    }
    
    // 页面加载完成后创建切换器
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createLanguageSwitcher);
    } else {
        createLanguageSwitcher();
    }
})();
