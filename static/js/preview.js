class PreviewManager {
    constructor() {
        this.previewContainer = document.getElementById('preview-container');
        this.initEventListeners();
    }
    
    initEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('close-preview') || 
                e.target.closest('.close-preview')) {
                this.hidePreview();
            }
            
            if (e.target === this.previewContainer) {
                this.hidePreview();
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.previewContainer.classList.contains('active')) {
                this.hidePreview();
            }
        });
    }
    
    async showPreview(fileId, fileType) {
        try {
            const response = await fetch(`/file/${fileId}/preview/`);
            if (!response.ok) {
                throw new Error('Failed to load preview');
            }
            
            const html = await response.text();
            this.updatePreviewContent(html);
            this.previewContainer.classList.add('active');
            document.body.style.overflow = 'hidden';
            
        } catch (error) {
            console.error('Preview error:', error);
            this.showError('Unable to load preview');
        }
    }
    
    updatePreviewContent(html) {
        const contentElement = this.previewContainer.querySelector('.preview-content');
        contentElement.innerHTML = html;
    }
    
    hidePreview() {
        this.previewContainer.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    showError(message) {
        const contentElement = this.previewContainer.querySelector('.preview-content');
        contentElement.innerHTML = `
            <div class="text-center py-8">
                <div class="text-5xl mb-4 text-danger">❌</div>
                <h4 class="mb-2">Error</h4>
                <p class="text-muted">${message}</p>
            </div>
        `;
        this.previewContainer.classList.add('active');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.previewManager = new PreviewManager();
    
    document.querySelectorAll('.preview-file').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const fileId = button.dataset.fileId;
            const fileType = button.dataset.fileType;
            window.previewManager.showPreview(fileId, fileType);
        });
    });
});