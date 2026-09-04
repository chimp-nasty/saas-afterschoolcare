export type ListLocationServiceDaysFilterRequest = {
	date_from?: string | null
	date_to?: string | null
	is_open?: boolean | null
}

export type LocationServiceDayTableResponse = {
	id: string
	location_service_id: string
	service_type_id: number

	service_name: string
	service_date: string

	is_open: boolean
	capacity: number
}