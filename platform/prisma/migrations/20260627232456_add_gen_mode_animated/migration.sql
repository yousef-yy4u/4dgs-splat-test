-- CreateEnum
CREATE TYPE "GenMode" AS ENUM ('STATIC', 'ANIMATED');

-- AlterTable
ALTER TABLE "Asset" ADD COLUMN     "animated" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "genMode" "GenMode" NOT NULL DEFAULT 'STATIC';
