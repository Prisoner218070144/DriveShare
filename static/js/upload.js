class FileUploader {
    constructor() {
        this.csrftoken = csrftoken;
    }
    
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('csrfmiddlewaretoken', this.csrftoken);
        
        try {
            const response = await fetch('/upload/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrftoken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Upload failed: ${response.status} ${response.statusText}\n${errorText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    }
}

class DragDropUpload {
    constructor(dropZoneElement) {
        this.dropZone = dropZoneElement;
        this.fileInput = dropZoneElement.querySelector('input[type="file"]');
        this.progressBar = dropZoneElement.querySelector('.upload-progress');
        this.uploader = new FileUploader();
        this.init();
    }
    
    init() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.preventDefaults.bind(this));
            this.dropZone.addEventListener(eventName, this.preventDefaults.bind(this));
        });
        
        // Highlight drop zone when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.add('dragover');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.remove('dragover');
            });
        });
        
        // Handle dropped files
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this));
        
        // Handle file input change
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Click on drop zone to trigger file input
        this.dropZone.addEventListener('click', () => {
            this.fileInput.click();
        });
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = Array.from(dt.files);
        this.handleFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.handleFiles(files);
    }
    
    async handleFiles(files) {
        const uploadQueue = document.getElementById('upload-queue');
        const queueItems = document.getElementById('queue-items');
        
        if (uploadQueue && queueItems) {
            uploadQueue.style.display = 'block';
            queueItems.innerHTML = '';
        }
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            let queueItem, statusDiv;
            if (uploadQueue && queueItems) {
                queueItem = document.createElement('div');
                queueItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded mb-2';
                queueItem.innerHTML = `
                    <div class="flex items-center gap-3">
                        <div class="text-2xl">
                            ${this.getFileIcon(file.type)}
                        </div>
                        <div>
                            <div class="font-medium">${file.name}</div>
                            <div class="text-sm text-gray-500">
                                ${formatFileSize(file.size)} • ${file.type || 'Unknown type'}
                            </div>
                        </div>
                    </div>
                    <div class="upload-status">
                        <span class="text-sm text-gray-500">Pending</span>
                    </div>
                `;
                queueItems.appendChild(queueItem);
                statusDiv = queueItem.querySelector('.upload-status');
            }
            
            try {
                if (statusDiv) {
                    statusDiv.innerHTML = '<span class="text-blue-500">Uploading...</span>';
                }
                
                this.showProgress();
                
                const result = await this.uploader.uploadFile(file);
                
                if (statusDiv) {
                    statusDiv.innerHTML = '<span class="text-green-500">✓ Uploaded</span>';
                }
                
                NotificationSystem.show(`Uploaded: ${file.name}`, 'success');
                
            } catch (error) {
                if (statusDiv) {
                    statusDiv.innerHTML = `<span class="text-red-500">✗ Failed</span>`;
                }
                NotificationSystem.show(`Failed to upload ${file.name}: ${error.message}`, 'error');
            }
        }
        
        this.progressBar.style.display = 'none';
        
        // Reload page after 2 seconds to show new files
        setTimeout(() => {
            window.location.reload();
        }, 2000);
    }
    
    showProgress() {
        this.progressBar.style.display = 'block';
        this.progressBar.style.width = '0%';
        
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) {
                clearInterval(interval);
            } else {
                width += 10;
                this.progressBar.style.width = width + '%';
            }
        }, 200);
    }
    
    getFileIcon(mimeType) {
        if (mimeType.startsWith('image/')) return '🖼️';
        if (mimeType.startsWith('video/')) return '🎬';
        if (mimeType.startsWith('audio/')) return '🎵';
        if (mimeType.includes('pdf')) return '📄';
        if (mimeType.includes('document')) return '📝';
        return '📁';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('CSRF Token:', csrftoken ? 'Found (' + csrftoken.length + ' chars)' : 'Not found');
    
    const dropZone = document.getElementById('upload-dropzone');
    if (dropZone) {
        new DragDropUpload(dropZone);
    }
});