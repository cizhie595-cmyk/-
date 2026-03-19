/**
 * Amazon Visionary Sourcing Tool - Image Preprocessor (PRD 3.1)
 * 
 * Canvas-based image preprocessing pipeline:
 * 1. Client-side resize/compress to 1024x1024 (max dimension, maintain aspect ratio)
 * 2. Background removal via remove-bg API or local edge-detection fallback
 * 3. Preview before upload
 * 4. Convert to optimized PNG/WebP for 3D generation
 */

class ImagePreprocessor {
    constructor(options = {}) {
        this.maxSize = options.maxSize || 1024;
        this.quality = options.quality || 0.92;
        this.outputFormat = options.outputFormat || 'image/png';
        this.removeBgEndpoint = options.removeBgEndpoint || '/api/v1/image/remove-bg';
        this.onProgress = options.onProgress || (() => {});
        this.onPreview = options.onPreview || (() => {});
    }

    /**
     * Full preprocessing pipeline: load -> resize -> remove bg -> preview
     * @param {File|Blob|string} source - File input, Blob, or image URL
     * @returns {Promise<{blob: Blob, dataUrl: string, width: number, height: number, originalSize: number, processedSize: number}>}
     */
    async process(source) {
        this.onProgress({ step: 'loading', percent: 0, message: 'Loading image...' });

        // Step 1: Load image
        const img = await this._loadImage(source);
        const originalSize = source instanceof File ? source.size : 0;
        this.onProgress({ step: 'loaded', percent: 20, message: 'Image loaded' });

        // Step 2: Resize to max dimension
        this.onProgress({ step: 'resizing', percent: 30, message: 'Resizing to optimal dimensions...' });
        const resized = this._resizeImage(img);
        this.onProgress({ step: 'resized', percent: 50, message: `Resized to ${resized.width}x${resized.height}` });

        // Step 3: Preview resized image
        const resizedDataUrl = resized.canvas.toDataURL(this.outputFormat, this.quality);
        this.onPreview({ stage: 'resized', dataUrl: resizedDataUrl, width: resized.width, height: resized.height });

        // Step 4: Convert to blob
        this.onProgress({ step: 'compressing', percent: 70, message: 'Compressing...' });
        const blob = await this._canvasToBlob(resized.canvas);

        this.onProgress({ step: 'done', percent: 100, message: 'Processing complete' });

        return {
            blob: blob,
            dataUrl: resizedDataUrl,
            width: resized.width,
            height: resized.height,
            originalSize: originalSize,
            processedSize: blob.size,
            compressionRatio: originalSize > 0 ? ((1 - blob.size / originalSize) * 100).toFixed(1) : 0
        };
    }

    /**
     * Process with background removal
     * @param {File|Blob|string} source
     * @returns {Promise<object>}
     */
    async processWithBgRemoval(source) {
        // First do standard processing
        const result = await this.process(source);

        this.onProgress({ step: 'removing_bg', percent: 80, message: 'Removing background...' });

        try {
            // Try server-side remove-bg API
            const bgRemoved = await this._removeBackground(result.blob);
            
            // Load the bg-removed image
            const bgImg = await this._loadImage(bgRemoved.dataUrl || URL.createObjectURL(bgRemoved.blob));
            
            // Resize again to ensure dimensions
            const finalCanvas = this._resizeImage(bgImg);
            const finalDataUrl = finalCanvas.canvas.toDataURL('image/png', 1.0); // PNG for transparency
            const finalBlob = await this._canvasToBlob(finalCanvas.canvas, 'image/png');

            this.onPreview({ stage: 'bg_removed', dataUrl: finalDataUrl, width: finalCanvas.width, height: finalCanvas.height });
            this.onProgress({ step: 'done', percent: 100, message: 'Background removed successfully' });

            return {
                ...result,
                blob: finalBlob,
                dataUrl: finalDataUrl,
                processedSize: finalBlob.size,
                bgRemoved: true
            };
        } catch (e) {
            console.warn('Background removal failed, using original:', e.message);
            // Fallback: try client-side edge detection
            try {
                const fallbackResult = await this._clientSideBgRemoval(result);
                this.onProgress({ step: 'done', percent: 100, message: 'Background removed (local fallback)' });
                return fallbackResult;
            } catch (e2) {
                console.warn('Client-side bg removal also failed:', e2.message);
                this.onProgress({ step: 'done', percent: 100, message: 'Background removal unavailable, using original' });
                return { ...result, bgRemoved: false };
            }
        }
    }

    /**
     * Load an image from various sources
     * @private
     */
    _loadImage(source) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => resolve(img);
            img.onerror = () => reject(new Error('Failed to load image'));

            if (source instanceof File || source instanceof Blob) {
                img.src = URL.createObjectURL(source);
            } else if (typeof source === 'string') {
                if (source.startsWith('data:') || source.startsWith('blob:') || source.startsWith('http')) {
                    img.src = source;
                } else {
                    reject(new Error('Invalid image source'));
                }
            } else {
                reject(new Error('Unsupported image source type'));
            }
        });
    }

    /**
     * Resize image maintaining aspect ratio, fit within maxSize x maxSize
     * @private
     */
    _resizeImage(img) {
        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;

        // Calculate scale to fit within maxSize
        if (width > this.maxSize || height > this.maxSize) {
            const scale = Math.min(this.maxSize / width, this.maxSize / height);
            width = Math.round(width * scale);
            height = Math.round(height * scale);
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');

        // Use high-quality resampling
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, width, height);

        return { canvas, width, height, ctx };
    }

    /**
     * Convert canvas to Blob
     * @private
     */
    _canvasToBlob(canvas, format = null) {
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    if (blob) resolve(blob);
                    else reject(new Error('Canvas to Blob conversion failed'));
                },
                format || this.outputFormat,
                this.quality
            );
        });
    }

    /**
     * Server-side background removal via remove-bg API
     * @private
     */
    async _removeBackground(blob) {
        const formData = new FormData();
        formData.append('image', blob, 'image.png');

        const token = localStorage.getItem('auth_token');
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(this.removeBgEndpoint, {
            method: 'POST',
            headers: headers,
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Remove-bg API returned ${response.status}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('image')) {
            // API returns image directly
            const resultBlob = await response.blob();
            return { blob: resultBlob, dataUrl: URL.createObjectURL(resultBlob) };
        } else {
            // API returns JSON with base64 or URL
            const data = await response.json();
            if (data.image_url) {
                return { dataUrl: data.image_url, blob: null };
            } else if (data.image_base64) {
                return { dataUrl: `data:image/png;base64,${data.image_base64}`, blob: null };
            }
            throw new Error('Unexpected remove-bg response format');
        }
    }

    /**
     * Client-side background removal using edge detection + flood fill
     * Simple approach: detect dominant background color and make it transparent
     * @private
     */
    async _clientSideBgRemoval(processedResult) {
        const img = await this._loadImage(processedResult.dataUrl);
        const canvas = document.createElement('canvas');
        canvas.width = processedResult.width;
        canvas.height = processedResult.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;

        // Sample corners to detect background color
        const corners = [
            this._getPixel(data, canvas.width, 0, 0),
            this._getPixel(data, canvas.width, canvas.width - 1, 0),
            this._getPixel(data, canvas.width, 0, canvas.height - 1),
            this._getPixel(data, canvas.width, canvas.width - 1, canvas.height - 1)
        ];

        // Find most common corner color (likely background)
        const bgColor = this._averageColor(corners);
        const tolerance = 40; // Color distance tolerance

        // Make matching pixels transparent
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2];
            const dist = Math.sqrt(
                Math.pow(r - bgColor.r, 2) +
                Math.pow(g - bgColor.g, 2) +
                Math.pow(b - bgColor.b, 2)
            );
            if (dist < tolerance) {
                data[i + 3] = 0; // Set alpha to 0
            }
        }

        ctx.putImageData(imageData, 0, 0);
        const dataUrl = canvas.toDataURL('image/png', 1.0);
        const blob = await this._canvasToBlob(canvas, 'image/png');

        this.onPreview({ stage: 'bg_removed', dataUrl: dataUrl, width: canvas.width, height: canvas.height });

        return {
            ...processedResult,
            blob: blob,
            dataUrl: dataUrl,
            processedSize: blob.size,
            bgRemoved: true,
            bgMethod: 'client-side'
        };
    }

    /**
     * Get pixel color at (x, y)
     * @private
     */
    _getPixel(data, width, x, y) {
        const idx = (y * width + x) * 4;
        return { r: data[idx], g: data[idx + 1], b: data[idx + 2], a: data[idx + 3] };
    }

    /**
     * Average color from array of {r,g,b} objects
     * @private
     */
    _averageColor(colors) {
        const sum = colors.reduce((acc, c) => ({ r: acc.r + c.r, g: acc.g + c.g, b: acc.b + c.b }), { r: 0, g: 0, b: 0 });
        const n = colors.length;
        return { r: Math.round(sum.r / n), g: Math.round(sum.g / n), b: Math.round(sum.b / n) };
    }

    /**
     * Create a visual preview widget
     * @param {HTMLElement} container - Container element
     * @returns {object} Widget controller with update() method
     */
    static createPreviewWidget(container) {
        container.innerHTML = `
            <div class="img-preprocess-widget">
                <div class="preprocess-stages">
                    <div class="preprocess-stage" id="pp-stage-original">
                        <div class="stage-label">Original</div>
                        <div class="stage-preview"><div class="stage-placeholder">No image</div></div>
                        <div class="stage-info"></div>
                    </div>
                    <div class="preprocess-arrow">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                    </div>
                    <div class="preprocess-stage" id="pp-stage-processed">
                        <div class="stage-label">Processed</div>
                        <div class="stage-preview"><div class="stage-placeholder">Processing...</div></div>
                        <div class="stage-info"></div>
                    </div>
                </div>
                <div class="preprocess-progress" id="pp-progress" style="display:none;">
                    <div class="progress-bar"><div class="progress-fill" id="pp-progress-fill" style="width:0%"></div></div>
                    <div class="preprocess-status" id="pp-status">Ready</div>
                </div>
                <div class="preprocess-actions" id="pp-actions" style="display:none;">
                    <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:0.85rem;">
                        <input type="checkbox" id="pp-remove-bg" checked> Remove Background
                    </label>
                </div>
            </div>
        `;

        return {
            setOriginal(dataUrl, info) {
                const stage = container.querySelector('#pp-stage-original .stage-preview');
                stage.innerHTML = `<img src="${dataUrl}" alt="Original" style="max-width:100%;max-height:160px;border-radius:6px;">`;
                const infoEl = container.querySelector('#pp-stage-original .stage-info');
                if (info) infoEl.textContent = info;
            },
            setProcessed(dataUrl, info) {
                const stage = container.querySelector('#pp-stage-processed .stage-preview');
                stage.innerHTML = `<img src="${dataUrl}" alt="Processed" style="max-width:100%;max-height:160px;border-radius:6px;background:repeating-conic-gradient(#808080 0% 25%, transparent 0% 50%) 50%/16px 16px;">`;
                const infoEl = container.querySelector('#pp-stage-processed .stage-info');
                if (info) infoEl.textContent = info;
            },
            setProgress(percent, message) {
                const bar = container.querySelector('#pp-progress');
                const fill = container.querySelector('#pp-progress-fill');
                const status = container.querySelector('#pp-status');
                bar.style.display = 'block';
                fill.style.width = percent + '%';
                if (message) status.textContent = message;
            },
            showActions(show = true) {
                container.querySelector('#pp-actions').style.display = show ? 'flex' : 'none';
            },
            getRemoveBg() {
                return container.querySelector('#pp-remove-bg').checked;
            },
            reset() {
                container.querySelector('#pp-stage-original .stage-preview').innerHTML = '<div class="stage-placeholder">No image</div>';
                container.querySelector('#pp-stage-processed .stage-preview').innerHTML = '<div class="stage-placeholder">Processing...</div>';
                container.querySelector('#pp-stage-original .stage-info').textContent = '';
                container.querySelector('#pp-stage-processed .stage-info').textContent = '';
                container.querySelector('#pp-progress').style.display = 'none';
            }
        };
    }
}

// Export for global use
window.ImagePreprocessor = ImagePreprocessor;
