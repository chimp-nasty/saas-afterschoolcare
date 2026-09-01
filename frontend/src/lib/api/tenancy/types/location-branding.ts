export type PublicLocationResponse = {
    tenant_name: string;
    tenant_code: string;

    location_code: string;
    location_name: string;

    display_name?: string;
    logo_key?: string;

    primary_color?: string;
    secondary_color?: string;
    font_family?: string;
}