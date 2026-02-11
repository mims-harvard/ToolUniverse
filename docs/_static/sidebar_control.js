// Custom sidebar expansion control
// This script allows per-section control of sidebar expansion
// 
// HOW TO USE:
// Add data-expand="true" to any page's metadata to expand it in sidebar
// This is controlled by adding :expand: to toctree entries (see below)

document.addEventListener('DOMContentLoaded', function() {
    // Read expansion config from page metadata
    // Pages can be marked with data-expand attribute in their HTML
    const expandedPages = new Set();
    
    // Check for pages marked with expand in the document
    document.querySelectorAll('[data-expand="true"]').forEach(function(el) {
        const href = el.getAttribute('href');
        if (href) {
            expandedPages.add(href);
        }
    });
    
    // Define which sections should be expanded by default
    // Add any section title here with true to expand it, false to collapse it
    // 
    // USAGE: Just add the exact text that appears in the sidebar
    // Example: 'Python Developer Guide': true,
    //
    const expansionConfig = {
        // Top-level sections (captions from toctree)
        '🚀 Get Started': false,           // Keep collapsed
        '💡 Tutorials & Workflows': false,
        '⚙️ Advanced Features': false,
        '🔨 Expand ToolUniverse': false,
        '🔧 Tools Catalog': false,
        '🔌 API Reference': false,
        '❓ Help & Reference': false,
        
        // Second-level sections (pages)
        'Python Developer Guide': true,    // ✅ EXPAND - shows all Python API pages
        'Choose Your AI Agent Platform': false,
        
        // Third-level sections (if needed)
        'Platform Setup Guides': false,
        'MCP & Integration': false,
    };
    
    // Function to expand/collapse sections based on config
    function applyExpansionConfig() {
        // Find all navigation items
        const navItems = document.querySelectorAll('.toctree-l1, .toctree-l2, .toctree-l3, .toctree-l4');
        
        navItems.forEach(function(item) {
            const link = item.querySelector('a');
            if (!link) return;
            
            const text = link.textContent.trim();
            const href = link.getAttribute('href');
            
            // Check if this section should be expanded
            let shouldExpand = false;
            
            // Check manual config
            if (text in expansionConfig) {
                shouldExpand = expansionConfig[text];
            }
            
            // Check if href is in expandedPages
            if (href && expandedPages.has(href)) {
                shouldExpand = true;
            }
            
            const hasChildren = item.querySelector('ul');
            
            if (hasChildren && shouldExpand) {
                // Expand: remove 'closed' class, add 'open' class
                item.classList.remove('closed');
                item.classList.add('open');
                const childList = item.querySelector('ul');
                if (childList) {
                    childList.style.display = 'block';
                }
            }
        });
    }
    
    // Apply the configuration
    applyExpansionConfig();
    
    // Re-apply after any dynamic updates (if needed)
    setTimeout(applyExpansionConfig, 100);
    setTimeout(applyExpansionConfig, 500);
});
