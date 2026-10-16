export type Pagination = {
    page?: number;
    limit?: number;
};

export type PaginationLoadMode =
    | 'replace'
    | 'append';
