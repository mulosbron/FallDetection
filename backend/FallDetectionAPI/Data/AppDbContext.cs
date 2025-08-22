using Microsoft.EntityFrameworkCore;
using FallDetectionAPI.Models;

namespace FallDetectionAPI.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<FallDetection> FallDetections { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // FallDetection configuration - AI Service ile aynı tablo
        modelBuilder.Entity<FallDetection>(entity =>
        {
            entity.ToTable("fall_detections");
            entity.HasKey(e => e.Id);
            
            // Property mappings
            entity.Property(e => e.ImageHash)
                .HasColumnName("image_hash")
                .IsRequired()
                .HasMaxLength(64);
                
            entity.Property(e => e.Result)
                .IsRequired()
                .HasMaxLength(10);
                
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .HasDefaultValueSql("CURRENT_TIMESTAMP")
                .HasColumnType("timestamp without time zone");
                
            entity.Property(e => e.ImageSize)
                .HasColumnName("image_size")
                .HasMaxLength(20);
                
            entity.Property(e => e.ProcessingTimeMs)
                .HasColumnName("processing_time_ms");
            
            // Indexes
            entity.HasIndex(e => e.ImageHash)
                .IsUnique()
                .HasDatabaseName("idx_image_hash");
                
            entity.HasIndex(e => e.CreatedAt)
                .HasDatabaseName("idx_created_at");
        });
    }
}
