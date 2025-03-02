document.addEventListener('DOMContentLoaded', function() {
    console.log('Flashcard script loaded, looking for flip cards...');
    
    // Add click event to all flashcards
    const flipCards = document.querySelectorAll('.flip-card');
    
    if (flipCards.length === 0) {
        console.warn('No flip-card elements found on the page!');
        return;
    }
    
    console.log(`Found ${flipCards.length} flip cards, attaching click events...`);
    
    flipCards.forEach((card, index) => {
        console.log(`Setting up card ${index + 1}`);
        
        card.addEventListener('click', function(e) {
            // Prevent flipping when clicking the edit button
            if (e.target.classList.contains('edit-btn') || 
                e.target.closest('.edit-btn')) {
                console.log('Edit button clicked, preventing flip');
                return;
            }
            
            // Prevent flipping when clicking on a clickable image
            if (e.target.classList.contains('clickable-image')) {
                console.log('Image clicked, preventing flip');
                return;
            }
            
            console.log(`Flipping card ${index + 1}`);
            this.classList.toggle('flipped');
        });
    });
    
    console.log('All flip card events successfully attached!');
});
