var excelDownloadState = {
    allSelected: false,
    selectedIds: new Set(),   // used when allSelected is false: ids explicitly checked
    excludedIds: new Set()    // used when allSelected is true: ids unchecked out of "all"
};

/**
 * Extract the data id from an access_data_url value (e.g. ".../data?id=42")
 * @param {string} value
 * @returns {string|null}
 */
var getDataIdFromCheckboxValue = function(value) {
    if (!value) return null;
    var match = value.match(/[?&]id=([^&]+)/);
    return match ? match[1] : null;
};

/**
 * Re-apply the current selection state (Select All / individually selected ids)
 * to whatever checkboxes are currently in the DOM. Called on init and after
 * every paginated results reload so selections survive changing pages.
 * @param {jQuery} [$scope] optional container to restrict to (defaults to whole document)
 */
var applyExcelSelectionState = function($scope) {
    ($scope || $(document)).find('.excel-select-checkbox').each(function() {
        var id = getDataIdFromCheckboxValue($(this).val());
        var checked = excelDownloadState.allSelected
            ? !excelDownloadState.excludedIds.has(id)
            : excelDownloadState.selectedIds.has(id);
        $(this).prop('checked', checked);
    });
};

/**
 * Sum up the "N results" badges (one per data source tab) to get the total
 * number of records currently matched by the query.
 * @returns {number}
 */
var getTotalResultsCount = function() {
    var total = 0;
    $('[id^="results_infos_"]').each(function() {
        var count = parseInt($(this).text(), 10);
        if (!isNaN(count)) total += count;
    });
    return total;
};

var hasExcelSelection = function() {
    return excelDownloadState.allSelected || excelDownloadState.selectedIds.size > 0;
};

var updateExcelDownloadButtonsLabel = function() {
    var label = '<i class="fas fa-download"></i> Download';
    if (excelDownloadState.allSelected) {
        var count = getTotalResultsCount() - excelDownloadState.excludedIds.size;
        label += ' (' + count + ')';
    } else if (excelDownloadState.selectedIds.size > 0) {
        label += ' (' + excelDownloadState.selectedIds.size + ')';
    }
    $('.download-excel-button').html(label).prop('disabled', !hasExcelSelection());
};

var updateSelectAllButtonsLabel = function() {
    var label = excelDownloadState.allSelected
        ? '<i class="fas fa-square"></i> Select None'
        : '<i class="fas fa-check-square"></i> Select All';
    $('.select-all-toggle-button').html(label);
};

/**
 * True while a download request is in flight, used to stop a double-click
 * (or clicking again before the first one resolves) from firing a second,
 * overlapping export that could race the first one server-side.
 */
var excelDownloadInProgress = false;

var finishExcelDownloadUI = function() {
    excelDownloadInProgress = false;
    updateExcelDownloadButtonsLabel();
    hideLoading();
};

/**
 * Poll the download status endpoint until the generated Excel file is ready,
 * then trigger the browser download.
 * @param {string} task_id
 */
var pollExcelDownloadStatus = function(task_id) {
    fetch('/download-status/?task_id=' + encodeURIComponent(task_id))
        .then(function(response) { return response.json(); })
        .then(function(status) {
            if (status.ready && status.download_url) {
                finishExcelDownloadUI();
                var link = document.createElement('a');
                link.href = status.download_url;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else if (status.state === 'FAILURE') {
                finishExcelDownloadUI();
                alert('File generation failed');
            } else {
                setTimeout(function() { pollExcelDownloadStatus(task_id); }, 2000);
            }
        })
        .catch(function(err) {
            finishExcelDownloadUI();
            alert('Error fetching download status');
            console.error(err);
        });
};

document.addEventListener('DOMContentLoaded', function() {
    var query_id_el = document.getElementById('query_id');

    // Nothing is selected yet, so the button starts disabled
    updateExcelDownloadButtonsLabel();

    // Toggle Select All / Select None
    $(document).on('click', '.select-all-toggle-button', function(event) {
        event.preventDefault();
        excelDownloadState.allSelected = !excelDownloadState.allSelected;
        excelDownloadState.selectedIds.clear();
        excelDownloadState.excludedIds.clear();
        applyExcelSelectionState();
        updateSelectAllButtonsLabel();
        updateExcelDownloadButtonsLabel();
    });

    // Individual row selection
    $(document).on('change', '.excel-select-checkbox', function() {
        var id = getDataIdFromCheckboxValue($(this).val());
        if (!id) return;

        if (excelDownloadState.allSelected) {
            // Stay in "all" mode; just track this one row as an exception
            if ($(this).is(':checked')) {
                excelDownloadState.excludedIds.delete(id);
            } else {
                excelDownloadState.excludedIds.add(id);
            }
        } else if ($(this).is(':checked')) {
            excelDownloadState.selectedIds.add(id);
        } else {
            excelDownloadState.selectedIds.delete(id);
        }
        updateExcelDownloadButtonsLabel();
    });

    // Download button
    $(document).on('click', '.download-excel-button', function(event) {
        event.preventDefault();
        if (excelDownloadInProgress || !hasExcelSelection()) return;
        $('#download-excel-confirm-modal').modal('show');
    });

    $('#download-excel-confirm-yes').on('click', function() {
        $('#download-excel-confirm-modal').modal('hide');
        if (excelDownloadInProgress || !hasExcelSelection()) return;

        var url, payload;
        if (excelDownloadState.allSelected) {
            var query_id = query_id_el ? (query_id_el.textContent || query_id_el.innerText) : null;
            if (!query_id) {
                alert('Error in extraction, please reload the page.');
                return;
            }
            url = '/download-all-data/';
            payload = { query_id: query_id };
            if (excelDownloadState.excludedIds.size > 0) {
                payload.exclude_ids = Array.from(excelDownloadState.excludedIds);
            }
        } else {
            url = '/download-selected-data/';
            payload = { id_list: Array.from(excelDownloadState.selectedIds) };
        }

        excelDownloadInProgress = true;
        $('.download-excel-button').prop('disabled', true);
        showLoading();

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(payload),
        })
        .then(function(response) {
            if (!response.ok) {
                return response.text().then(function(text) { return Promise.reject(text || 'Error'); });
            }
            return response.json();
        })
        .then(function(data) {
            if (!data.task_id) {
                throw new Error('No task_id returned');
            }
            pollExcelDownloadStatus(data.task_id);
        })
        .catch(function(err) {
            finishExcelDownloadUI();
            alert('Download failed: ' + err);
            console.error(err);
        });
    });
});
