import './Pagination.css';

const Pagination = ({ currentPage, totalPages, totalItems, onPageChange }) => {
    const handlePrevious = () => {
        if (currentPage > 1) {
            onPageChange(currentPage - 1);
        }
    };

    const handleNext = () => {
        if (currentPage < totalPages) {
            onPageChange(currentPage + 1);
        }
    };

    const startItem = (currentPage - 1) * 5 + 1;
    const endItem = Math.min(currentPage * 5, totalItems);

    return (
        <div className="pagination">
            <div className="pagination-info">
                Mostrando {startItem} a {endItem} de {totalItems} resultados
            </div>

            <div className="pagination-controls">
                <button
                    className="pagination-btn"
                    onClick={handlePrevious}
                    disabled={currentPage === 1}
                    aria-label="Página anterior"
                >
                    ‹
                </button>

                <button
                    className="pagination-btn"
                    onClick={handleNext}
                    disabled={currentPage === totalPages}
                    aria-label="Página siguiente"
                >
                    ›
                </button>
            </div>
        </div>
    );
};

export default Pagination;
