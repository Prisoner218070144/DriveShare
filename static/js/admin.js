class DriveExplorer {
    constructor() {
        this.currentPath = 'F:/';
        this.history = [];
        this.init();
    }
    
    init() {
        this.loadDirectory(this.currentPath);
        
        const backBtn = document.getElementById('btn-back');
        const refreshBtn = document.getElementById('btn-refresh');
        const driveSelector = document.getElementById('drive-selector');
        
        if (backBtn) backBtn.addEventListener('click', () => this.goBack());
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.refresh());
        if (driveSelector) driveSelector.addEventListener('change', (e) => {
            this.currentPath = e.target.value;
            this.loadDirectory(this.currentPath);
        });
        
        const closeBtn = document.querySelector('.close-preview');
        if (closeBtn) closeBtn.addEventListener('click', () => {
            const previewPanel = document.getElementById('preview-panel');
            if (previewPanel) previewPanel.classList.remove('active');
        });
    }
    
    async loadDirectory(path) {
        try {
            const response = await fetch(`/admin/drive-access/?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.currentPath = data.path;
            this.updateUI(data);
            
        } catch (error) {
            this.showError(`Failed to load directory: ${error.message}`);
        }
    }
    
    updateUI(data) {
        const pathElement = document.getElementById('current-path');
        if (pathElement) {
            pathElement.textContent = data.path;
        }
        
        const backBtn = document.getElementById('btn-back');
        if (backBtn) {
            backBtn.disabled = !data.parent;
        }
        
        const container = document.getElementById('explorer-content');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (data.items.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <div class="text-4xl mb-4">📁</div>
                    <h3 class="mb-2">Empty Directory</h3>
                    <p class="text-muted">This directory is empty</p>
                </div>
            `;
            return;
        }
        
        data.items.forEach(item => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.dataset.path = item.path;
            fileItem.dataset.isDir = item.is_dir;
            
            const icon = item.is_dir ? '📁' : this.getFileIcon(item.name);
            const size = item.is_dir ? '' : formatFileSize(item.size);
            
            fileItem.innerHTML = `
                <div class="file-icon">${icon}</div>
                <div class="file-info">
                    <div class="file-name">${escapeHtml(item.name)}</div>
                    <div class="file-meta">
                        ${item.is_dir ? 'Directory' : `File • ${size}`}
                    </div>
                </div>
            `;
            
            fileItem.addEventListener('click', () => {
                if (item.is_dir) {
                    this.history.push(this.currentPath);
                    this.loadDirectory(item.path);
                } else {
                    this.previewFile(item.path);
                }
            });
            
            container.appendChild(fileItem);
        });
    }
    
    async previewFile(filePath) {
        try {
            const response = await fetch(`/admin/file-preview/?path=${encodeURIComponent(filePath)}`);
            const data = await response.json();
            
            const previewPanel = document.getElementById('preview-panel');
            const previewContent = document.getElementById('preview-content');
            
            if (!previewPanel || !previewContent) return;
            
            if (data.type === 'text') {
                previewContent.innerHTML = `
                    <h4 class="mb-2">${escapeHtml(filePath.split('/').pop())}</h4>
                    <p class="text-muted mb-4">${formatFileSize(data.size)}</p>
                    <div class="preview-text">${escapeHtml(data.content)}</div>
                `;
            } else {
                previewContent.innerHTML = `
                    <div class="text-center py-8">
                        <div class="text-5xl mb-4">📄</div>
                        <h4 class="mb-2">${escapeHtml(filePath.split('/').pop())}</h4>
                        <p class="text-muted mb-4">${formatFileSize(data.size)} • Binary file</p>
                        <p class="text-muted">This file cannot be previewed in the browser</p>
                    </div>
                `;
            }
            
            previewPanel.classList.add('active');
            
        } catch (error) {
            this.showError(`Failed to preview file: ${error.message}`);
        }
    }
    
    goBack() {
        if (this.history.length > 0) {
            const previousPath = this.history.pop();
            this.loadDirectory(previousPath);
        }
    }
    
    refresh() {
        this.loadDirectory(this.currentPath);
    }
    
    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'];
        const videoExts = ['mp4', 'avi', 'mov', 'mkv', 'wmv'];
        const audioExts = ['mp3', 'wav', 'ogg', 'flac'];
        const docExts = ['pdf', 'doc', 'docx', 'txt', 'rtf'];
        
        if (imageExts.includes(ext)) return '🖼️';
        if (videoExts.includes(ext)) return '🎬';
        if (audioExts.includes(ext)) return '🎵';
        if (docExts.includes(ext)) return '📄';
        return '📁';
    }
    
    showError(message) {
        const container = document.getElementById('explorer-content');
        if (!container) return;
        
        container.innerHTML = `
            <div class="text-center py-8">
                <div class="text-4xl mb-4 text-danger">❌</div>
                <h3 class="mb-2 text-danger">Error</h3>
                <p class="text-muted">${message}</p>
                <button onclick="driveExplorer.refresh()" class="btn btn-primary mt-4">
                    Try Again
                </button>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('explorer-content')) {
        window.driveExplorer = new DriveExplorer();
    }
});