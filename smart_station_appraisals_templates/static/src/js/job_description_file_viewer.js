/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { download } from "@web/core/network/download";

/**
 * Open the native Odoo FileViewer overlay (same component used by Documents / chatter).
 */
async function openJobDescriptionFileViewer(env, action) {
    const params = action.params || {};
    const filename = params.filename || "file";
    const contentUrl = params.content_url;
    const previewUrl = params.preview_url;
    const mimetype = params.mimetype || "";

    if (!contentUrl) {
        return;
    }

    const downloadUrl = `${contentUrl}?download=true`;
    const inlineUrl = `${contentUrl}?download=false`;

    let file;
    if (params.is_pdf) {
        const encoded = encodeURIComponent(inlineUrl);
        file = {
            name: filename,
            mimetype: "application/pdf",
            isPdf: true,
            isImage: false,
            isText: false,
            isVideo: false,
            isUrlYoutube: false,
            isViewable: true,
            defaultSource: `/web/static/lib/pdfjs/web/viewer.html?file=${encoded}#pagemode=none`,
            downloadUrl,
        };
    } else if (params.is_image) {
        file = {
            name: filename,
            mimetype: mimetype || "image/png",
            isPdf: false,
            isImage: true,
            isText: false,
            isVideo: false,
            isUrlYoutube: false,
            isViewable: true,
            defaultSource: inlineUrl,
            downloadUrl,
        };
    } else if (params.is_docx) {
        // Show Word content inside FileViewer via HTML preview iframe
        file = {
            name: filename,
            mimetype: "text/plain",
            isPdf: false,
            isImage: false,
            isText: true,
            isVideo: false,
            isUrlYoutube: false,
            isViewable: true,
            defaultSource: previewUrl,
            downloadUrl,
        };
    } else {
        // Unsupported type: download like Documents does for non-previewable files
        download({ data: {}, url: downloadUrl });
        return;
    }

    const { open } = createFileViewer();
    open(file);
}

registry.category("actions").add("ss_job_description_file_viewer", openJobDescriptionFileViewer);
