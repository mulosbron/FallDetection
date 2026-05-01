using FallDetectionAPI.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace FallDetectionAPI.Persistence.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<FallDetectionRecord> FallDetections => Set<FallDetectionRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<FallDetectionRecord>(entity =>
        {
            entity.ToTable("fall_detections");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id");
            entity.Property(e => e.ImageHash).HasColumnName("image_hash").IsRequired().HasMaxLength(64);
            entity.Property(e => e.Result).HasColumnName("result").IsRequired().HasMaxLength(10);
            entity.Property(e => e.CameraIndex).HasColumnName("camera_index").HasDefaultValue(0);
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("CURRENT_TIMESTAMP").HasColumnType("timestamp without time zone");
            entity.Property(e => e.ImageSize).HasColumnName("image_size").HasMaxLength(20);
            entity.Property(e => e.ProcessingTimeMs).HasColumnName("processing_time_ms");

            entity.HasIndex(e => e.ImageHash).IsUnique().HasDatabaseName("idx_image_hash");
            entity.HasIndex(e => e.CreatedAt).HasDatabaseName("idx_created_at");
            entity.HasIndex(e => e.CameraIndex).HasDatabaseName("idx_camera_index");
        });
    }
}
