document.addEventListener('DOMContentLoaded', function() {
    // Add click event to all flashcards
    const flipCards = document.querySelectorAll('.flip-card');
    flipCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Prevent flipping when clicking the edit button
            if (e.target.classList.contains('edit-btn') || 
                e.target.closest('.edit-btn')) {
                return;
            }
            this.classList.toggle('flipped');
        });
    });
});
