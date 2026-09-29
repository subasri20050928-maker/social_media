/**
 * Mini Social Media Platform - Interactive JavaScript
 * Handles AJAX Likes, Follows, Comments, Deletions, Modals, and Notifications
 */

document.addEventListener('DOMContentLoaded', () => {
    initCSRF();
    initCharCounters();
    initLikes();
    initFollows();
    initComments();
    initPostDeletions();
    initCommentDeletions();
    initCommentToggles();
});

// Helper: Read CSRF cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

let csrfToken = '';

function initCSRF() {
    csrfToken = getCookie('csrftoken');
    if (!csrfToken) {
        // Fallback to meta tag or input
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            csrfToken = metaTag.getAttribute('content');
        } else {
            const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (input) csrfToken = input.value;
        }
    }
}

// Toast Notifications
function showToast(message, type = 'default') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'danger' ? 'toast-danger' : type === 'success' ? 'toast-success' : ''}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.2s ease';
        setTimeout(() => toast.remove(), 250);
    }, 3200);
}

// Confirmation Modal
function confirmAction(title, message, onConfirm) {
    const modal = document.getElementById('confirmation-modal');
    if (!modal) {
        if (confirm(message)) {
            onConfirm();
        }
        return;
    }

    const titleEl = modal.querySelector('.modal-header');
    const msgEl = modal.querySelector('.modal-body');
    const confirmBtn = modal.querySelector('.modal-confirm-btn');
    const cancelBtn = modal.querySelector('.modal-cancel-btn');

    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;

    const cleanup = () => {
        modal.classList.remove('active');
        confirmBtn.removeEventListener('click', handleConfirm);
        cancelBtn.removeEventListener('click', handleCancel);
    };

    const handleConfirm = () => {
        cleanup();
        onConfirm();
    };

    const handleCancel = () => {
        cleanup();
    };

    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);
    modal.classList.add('active');
}

// 1. Like / Unlike Post (AJAX)
function initLikes() {
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const postId = btn.getAttribute('data-post-id');
            if (!postId) return;

            // Optimistic UI state
            const isCurrentlyLiked = btn.classList.contains('liked');
            const countSpan = btn.querySelector('.like-count');
            let count = parseInt(countSpan.textContent) || 0;

            btn.classList.toggle('liked', !isCurrentlyLiked);
            countSpan.textContent = isCurrentlyLiked ? Math.max(0, count - 1) : count + 1;

            try {
                const response = await fetch(`/post/${postId}/like/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) throw new Error('Network error');

                const data = await response.json();
                if (data.success) {
                    btn.classList.toggle('liked', data.is_liked);
                    countSpan.textContent = data.likes_count;
                } else {
                    // Rollback
                    btn.classList.toggle('liked', isCurrentlyLiked);
                    countSpan.textContent = count;
                    showToast(data.error || 'Failed to update like', 'danger');
                }
            } catch (err) {
                // Rollback on error
                btn.classList.toggle('liked', isCurrentlyLiked);
                countSpan.textContent = count;
                showToast('Something went wrong. Please try again.', 'danger');
            }
        });
    });
}

// 2. Follow / Unfollow User (AJAX)
function initFollows() {
    document.querySelectorAll('.follow-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const username = btn.getAttribute('data-username');
            if (!username) return;

            btn.disabled = true;

            try {
                const response = await fetch(`/user/${encodeURIComponent(username)}/follow/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();
                if (data.success) {
                    if (data.is_following) {
                        btn.textContent = 'Following';
                        btn.classList.add('following');
                    } else {
                        btn.textContent = 'Follow';
                        btn.classList.remove('following');
                    }

                    // Update followers count badge if present on profile
                    const followersCountEl = document.getElementById('followers-count');
                    if (followersCountEl) {
                        followersCountEl.textContent = data.followers_count;
                    }
                    showToast(data.is_following ? `You are now following ${username}` : `Unfollowed ${username}`);
                } else {
                    showToast(data.error || 'Could not perform follow action', 'danger');
                }
            } catch (err) {
                showToast('Unable to connect to server', 'danger');
            } finally {
                btn.disabled = false;
            }
        });
    });
}

// 3. Comment Submission (AJAX)
function initComments() {
    document.querySelectorAll('.comment-input-form').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const postId = form.getAttribute('data-post-id');
            const input = form.querySelector('.comment-input');
            const content = input.value.trim();

            if (!content) {
                input.focus();
                return;
            }

            const submitBtn = form.querySelector('.comment-submit-btn');
            if (submitBtn) submitBtn.disabled = true;

            try {
                const response = await fetch(`/post/${postId}/comment/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ content: content })
                });

                const data = await response.json();
                if (data.success) {
                    input.value = '';
                    
                    // Update comment count on post card
                    const commentCountBadge = document.querySelector(`.comment-count[data-post-id="${postId}"]`);
                    if (commentCountBadge) {
                        commentCountBadge.textContent = data.comments_count;
                    }

                    // Append comment to comments list
                    const commentsList = document.querySelector(`.comments-list[data-post-id="${postId}"]`);
                    if (commentsList) {
                        // Remove any empty notice if present
                        const emptyNotice = commentsList.querySelector('.empty-comments-notice');
                        if (emptyNotice) emptyNotice.remove();

                        const commentEl = renderCommentItem(data.comment);
                        commentsList.appendChild(commentEl);
                        wireSingleCommentDelete(commentEl.querySelector('.comment-delete-btn'));
                    }
                    showToast('Comment posted', 'success');
                } else {
                    showToast(data.error || 'Failed to post comment', 'danger');
                }
            } catch (err) {
                showToast('Network error while posting comment', 'danger');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    });
}

// Helper: Render Comment DOM node
function renderCommentItem(comment) {
    const div = document.createElement('div');
    div.className = 'comment-item';
    div.id = `comment-${comment.id}`;

    const avatarHtml = comment.avatar_url 
        ? `<img src="${escapeHtml(comment.avatar_url)}" alt="${escapeHtml(comment.author)}" class="avatar avatar-sm">`
        : `<div class="avatar avatar-sm"><span class="avatar-initials">${escapeHtml(comment.author.substring(0, 2).toUpperCase())}</span></div>`;

    const deleteHtml = comment.can_delete 
        ? `<button type="button" class="comment-delete-btn" data-comment-id="${comment.id}" title="Delete comment">
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
               <polyline points="3 6 5 6 21 6"></polyline>
               <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
             </svg>
           </button>`
        : '';

    div.innerHTML = `
        <a href="/profile/${encodeURIComponent(comment.author)}/">
            ${avatarHtml}
        </a>
        <div class="comment-bubble">
            <div class="comment-header">
                <div>
                    <a href="/profile/${encodeURIComponent(comment.author)}/" class="comment-author">
                        ${escapeHtml(comment.author)}
                    </a>
                    <span class="comment-date"> · ${escapeHtml(comment.created_at)}</span>
                </div>
                ${deleteHtml}
            </div>
            <div class="comment-text">${escapeHtml(comment.content)}</div>
        </div>
    `;

    return div;
}

// 4. Delete Post (with confirmation and AJAX)
function initPostDeletions() {
    document.querySelectorAll('.post-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const postId = btn.getAttribute('data-post-id');
            if (!postId) return;

            confirmAction('Delete Post', 'Are you sure you want to delete this post? This action cannot be undone.', async () => {
                try {
                    const response = await fetch(`/post/${postId}/delete/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    const data = await response.json();
                    if (data.success) {
                        const postCard = document.getElementById(`post-${postId}`);
                        if (postCard) {
                            postCard.style.transition = 'all 0.25s ease';
                            postCard.style.opacity = '0';
                            postCard.style.transform = 'translateY(10px)';
                            setTimeout(() => postCard.remove(), 250);
                        }
                        showToast('Post deleted successfully.', 'success');
                    } else {
                        showToast(data.error || 'Failed to delete post', 'danger');
                    }
                } catch (err) {
                    showToast('Network error while deleting post', 'danger');
                }
            });
        });
    });
}

// 5. Delete Comment
function initCommentDeletions() {
    document.querySelectorAll('.comment-delete-btn').forEach(btn => {
        wireSingleCommentDelete(btn);
    });
}

function wireSingleCommentDelete(btn) {
    if (!btn) return;
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        const commentId = btn.getAttribute('data-comment-id');
        if (!commentId) return;

        confirmAction('Delete Comment', 'Delete this comment?', async () => {
            try {
                const response = await fetch(`/comment/${commentId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();
                if (data.success) {
                    const commentItem = document.getElementById(`comment-${commentId}`);
                    if (commentItem) {
                        const commentsList = commentItem.closest('.comments-list');
                        commentItem.remove();

                        // Update comments count badge on post
                        if (commentsList) {
                            const postId = commentsList.getAttribute('data-post-id');
                            const countEl = document.querySelector(`.comment-count[data-post-id="${postId}"]`);
                            if (countEl) countEl.textContent = data.comments_count;
                        }
                    }
                    showToast('Comment deleted', 'success');
                } else {
                    showToast(data.error || 'Could not delete comment', 'danger');
                }
            } catch (err) {
                showToast('Network error while deleting comment', 'danger');
            }
        });
    });
}

// 6. Comment toggle accordion / expansion
function initCommentToggles() {
    document.querySelectorAll('.comment-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const postId = btn.getAttribute('data-post-id');
            const container = document.getElementById(`comments-${postId}`);
            if (container) {
                const isHidden = container.style.display === 'none';
                container.style.display = isHidden ? 'block' : 'none';
                if (isHidden) {
                    const input = container.querySelector('.comment-input');
                    if (input) input.focus();
                }
            }
        });
    });
}

// Character counter for post input
function initCharCounters() {
    const postInput = document.querySelector('.post-input');
    const counter = document.getElementById('post-char-count');
    if (postInput && counter) {
        const update = () => {
            const len = postInput.value.length;
            counter.textContent = `${len}/2000`;
            if (len > 1900) {
                counter.style.color = 'var(--danger)';
            } else {
                counter.style.color = 'var(--text-light)';
            }
        };
        postInput.addEventListener('input', update);
        update();
    }
}

// Escape HTML helper
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
