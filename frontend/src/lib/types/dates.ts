import { z } from "zod";

export const dateSchema = z.iso
    .date()
    .transform((value) => new Date(`${value}T00:00:00`));

export const dateTimeSchema = z.iso
    .datetime({ offset: true })
    .transform((value) => new Date(value));