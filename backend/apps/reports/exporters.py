import csv

from django.http import HttpResponse


def csv_response(filename: str, header: list[tuple[str, str]], rows: list[dict]) -> HttpResponse:
    """Builds a downloadable CSV. `header` is a list of (row_key, column_label)
    pairs -- the label is what the user sees, the key is looked up on each row
    dict, so the CSV columns stay decoupled from the report's internal field
    names and ordering."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow([label for _, label in header])
    for row in rows:
        writer.writerow([row.get(key, "") for key, _ in header])
    return response


def maybe_csv(request, filename, header, rows) -> HttpResponse | None:
    """Returns a CSV download when the caller asked for `?export=csv`, else
    None so the view falls through to its normal JSON response. `export` is
    used rather than DRF's reserved `format` query param."""
    if request.query_params.get("export") != "csv":
        return None
    return csv_response(filename, header, rows)
