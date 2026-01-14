class ShareManager {
    constructor() {
        this.csrftoken = getCookie('csrftoken');
    }
    
    async showShareModal(fileId) {
        try {
            const response = await fetch(`/file/${fileId}/share-info/`);
            const data = await response.json();
            
            this.createShareModal(fileId, data);
            
        } catch (error) {
            NotificationSystem.show('Failed to load share information', 'error');
        }
    }
    
    createShareModal(fileId, fileInfo) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>Share "${fileInfo.name}"</h3>
                    <button type="button" class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="share-form" class="share-form">
                        <div class="form-group">
                            <label for="email">User Email</label>
                            <input type="email" id="email" name="email" required class="form-control">
                        </div>
                        <div class="form-group">
                            <label for="permission">Permission Level</label>
                            <select id="permission" name="permission" class="form-control">
                                <option value="1">Read Only</option>
                                <option value="2">Read & Write</option>
                                <option value="4">Admin</option>
                            </select>
                        </div>
                        <div class="form-group mt-3">
                            <button type="submit" class="btn btn-primary w-full">Share File</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.getElementById('modal-container').appendChild(modal);
        
        modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        modal.querySelector('form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const shareData = {
                email: formData.get('email'),
                permission: parseInt(formData.get('permission'))
            };
            
            try {
                const response = await fetch(`/file/${fileId}/share/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrftoken
                    },
                    body: JSON.stringify(shareData)
                });
                
                if (response.ok) {
                    NotificationSystem.show('File shared successfully!', 'success');
                    modal.remove();
                } else {
                    throw new Error('Sharing failed');
                }
            } catch (error) {
                NotificationSystem.show('Error sharing file: ' + error.message, 'error');
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.shareManager = new ShareManager();
    
    document.querySelectorAll('.share-file').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            const fileId = button.dataset.fileId;
            await window.shareManager.showShareModal(fileId);
        });
    });
});