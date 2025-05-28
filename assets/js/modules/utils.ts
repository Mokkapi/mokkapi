// Basic HTML escaping helper
export function escapeHtml(unsafe: string) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Helper function to get badge class based on method
export function getBadgeClass(method: string) {
    switch (method?.toUpperCase()) {
        case 'GET': return 'bg-green-100 text-green-800 border border-green-300';
        case 'POST': return 'bg-blue-100 text-blue-800 border border-blue-300';
        case 'PUT': return 'bg-yellow-100 text-yellow-800 border border-yellow-300';
        case 'PATCH': return 'bg-orange-100 text-orange-800 border border-orange-300';
        case 'DELETE': return 'bg-red-100 text-red-800 border border-red-300';
        case 'OPTIONS': return 'bg-purple-100 text-purple-800 border border-purple-300';
        case 'HEAD': return 'bg-teal-100 text-teal-800 border border-teal-300';
        default: return 'bg-gray-100 text-gray-800 border border-gray-300';
    }
}
