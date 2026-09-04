export type ListChildrenFilterRequest = {
	is_active?: boolean | null
	review_status?: string[] | null
}

export type ChildResponse = {
	id: string
	location_id: string
	user_id: string

	first_name: string
	last_name: string
	dob: string

	medical_info: string | null
	allergy_info: string | null
	medication_info: string | null

	is_active: boolean
	review_status: string

	created_at: string
	updated_at: string
}

export type ChildTableResponse = {
	id: string
	location_id: string
	user_id: string

	first_name: string
	last_name: string
	dob: string

	is_active: boolean
	review_status: string
}