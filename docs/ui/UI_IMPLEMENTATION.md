# YottaFlex Fulfillment Control Tower — UI Implementation

The React/Vite dashboard has been rebuilt to closely follow the supplied YottaFlex UI reference.

## Screens implemented

1. Google OAuth login
2. Fulfillment Control Tower overview
3. Orders search/list
4. Order details and allocation decision
5. Shipments search/list
6. Shipment tracking timeline
7. Exceptions
8. Data Quality

## Data behavior

- Authentication uses the FastAPI Google OAuth session.
- Overview metrics are loaded from `/api/v1/overview`.
- Orders are loaded from `/api/v1/orders` and details/allocation from the corresponding order endpoints.
- Shipments and tracking timelines are loaded from `/api/v1/shipments`.
- Exceptions are loaded from `/api/v1/exceptions`.
- Data Quality is loaded from `/api/v1/data-quality` and is derived from operational database integrity checks.
- Ground-truth anomaly records are not exposed through operational decision endpoints.
- Customer, item count, carrier, and promise-specific fields display `—` where the current database schema does not contain that information rather than inventing values.

## Visual direction

- Navy YottaFlex sidebar
- White enterprise workspace
- Compact cards and tables
- Green allocation/healthy states
- Red exception/unallocated states
- Blue navigation and action states
- Google OAuth login screen with warehouse-inspired dark background
- Order and shipment drill-down pages matching the supplied reference layout
