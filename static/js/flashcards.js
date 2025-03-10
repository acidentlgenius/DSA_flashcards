document.addEventListener('DOMContentLoaded', function() {
    // Gather all cards once rather than calling querySelectorAll each time
    const flipCards = document.querySelectorAll('.flip-card');
    
    if (flipCards.length === 0) {
        return;
    }
    
    // Use event delegation to reduce the number of event listeners
    document.addEventListener('click', function(e) {
        // Find the closest flip-card parent
        const card = e.target.closest('.flip-card');
        
        if (!card) return; // Not clicking on a card
        
        // Don't flip when clicking on certain elements
        if (e.target.classList.contains('edit-btn') || 
            e.target.closest('.edit-btn') ||
            e.target.classList.contains('clickable-image')) {
            return;
        }
        
        // Toggle the flipped class
        card.classList.toggle('flipped');
    });
});
